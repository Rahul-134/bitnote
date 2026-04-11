from fastapi import APIRouter, HTTPException
from bitnote.core.database import get_db
from bitnote.core.security import hash_password, verify_password
from bitnote.schemas.auth_schema import SignupRequest, LoginRequest, google_LoginRequest

import os
import firebase_admin
from firebase_admin import credentials, auth

router = APIRouter(prefix="/auth", tags=["Auth"])

_firebase_key_path = os.path.join(os.path.dirname(__file__), "..", "..", "firebase_key.json")
cred = credentials.Certificate(_firebase_key_path)
firebase_admin.initialize_app(cred)


@router.post("/signup")
def signup(data: SignupRequest):
    db = get_db()

    existing = db.execute(
        "SELECT user_id FROM users WHERE email = ?",
        (data.email,),
    ).fetchone()

    if existing:
        raise HTTPException(status_code=400, detail="Email already registered")

    db.execute(
        """
        INSERT INTO users (username, email, password_hash)
        VALUES (?, ?, ?)
        """,
        (data.username, data.email, hash_password(data.password)),
    )
    db.commit()

    return {"message": "Signup successful"}


@router.post("/login")
def login(data: LoginRequest):
    db = get_db()

    user = db.execute(
        "SELECT * FROM users WHERE email = ?",
        (data.email,),
    ).fetchone()

    if not user:
        raise HTTPException(status_code=404, detail="Invalid email or user not found")

    if user["password_hash"] is None:
        raise HTTPException(status_code=400, detail="This account uses Google sign-in")

    if not verify_password(data.password, user["password_hash"]):
        raise HTTPException(status_code=401, detail="Incorrect password")

    return {
        "message": "Login successful",
        "user_id": user["user_id"],
        "username": user["username"],
    }


@router.post("/google")
def google_signin(data: google_LoginRequest):
    db = get_db()

    # 1️ Verify Google ID token
    try:
        decoded = auth.verify_id_token(data.id_token)
    except Exception:
        raise HTTPException(status_code=401, detail="Invalid Google token")

    # 2️ Extract VERIFIED data
    email = decoded.get("email")
    name = decoded.get("name")
    pic = decoded.get("photoURL")

    if not email:
        raise HTTPException(status_code=400, detail="Email not found in token")

    # 3️ Check if user already exists
    user = db.execute(
        "SELECT * FROM users WHERE email = ?",
        (email,),
    ).fetchone()

    # 4️ Existing user → login
    if user:
        return {
            "message": "Login successful",
            "user_id": user["user_id"],
            "username": user["username"],
            "status": "logged_in",
            "pic": pic
        }

    # 5️ New user → signup
    username = name or email.split("@")[0]

    db.execute(
        """
        INSERT INTO users (username, email, password_hash)
        VALUES (?, ?, ?)
        """,
        (username, email, None),
    )
    db.commit()

    new_user = db.execute(
        "SELECT * FROM users WHERE email = ?",
        (email,),
    ).fetchone()

    return {
        "message": "Signup successful",
        "user_id": new_user["user_id"],
        "username": new_user["username"],
        "status": "logged_in",
        "pic": pic
    }
