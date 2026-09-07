import os
from datetime import datetime, timedelta, timezone

import jwt
from passlib.context import CryptContext
from fastapi import Depends, HTTPException, Header
from bitnote.core.database import get_db

pwd_context = CryptContext(schemes=["argon2"], deprecated="auto")

JWT_ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60 * 24 * 7  # 1 week

_DEV_SECRET_KEY = "dev-insecure-secret-change-me"
SECRET_KEY = os.getenv("BITNOTE_SECRET_KEY", _DEV_SECRET_KEY)
if SECRET_KEY == _DEV_SECRET_KEY:
    print(
        "WARNING: BITNOTE_SECRET_KEY is not set. Using an insecure default "
        "signing key — do not use this in production."
    )


def hash_password(password: str) -> str:
    return pwd_context.hash(password)


def verify_password(password: str, hashed: str) -> bool:
    return pwd_context.verify(password, hashed)


def create_access_token(user_id: int, username: str) -> str:
    expire = datetime.now(timezone.utc) + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    payload = {
        "sub": str(user_id),
        "username": username,
        "exp": expire,
    }
    return jwt.encode(payload, SECRET_KEY, algorithm=JWT_ALGORITHM)


def get_current_user(
    authorization: str = Header(None),
    db=Depends(get_db),
):
    """
    Verifies the "Authorization: Bearer <token>" header and returns the
    authenticated user's row. This is the only source of user identity —
    endpoints must not trust a client-supplied user id.
    """

    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Missing or invalid authorization header")

    token = authorization[len("Bearer "):]

    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[JWT_ALGORITHM])
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Session expired")
    except jwt.InvalidTokenError:
        raise HTTPException(status_code=401, detail="Invalid token")

    user_id = payload.get("sub")
    if user_id is None:
        raise HTTPException(status_code=401, detail="Invalid token")

    cursor = db.execute(
        "SELECT * FROM users WHERE user_id = ?",
        (user_id,),
    )
    user = cursor.fetchone()

    if not user:
        raise HTTPException(status_code=401, detail="Invalid user")

    return dict(user)
