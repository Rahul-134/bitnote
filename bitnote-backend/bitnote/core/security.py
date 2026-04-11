from passlib.context import CryptContext
from fastapi import Depends, HTTPException, Header
from bitnote.core.database import get_db

pwd_context = CryptContext(schemes=["argon2"], deprecated="auto")


def hash_password(password: str) -> str:
    return pwd_context.hash(password)


def verify_password(password: str, hashed: str) -> bool:
    return pwd_context.verify(password, hashed)


def get_current_user(
    x_user_id: int = Header(None),
    db=Depends(get_db),
):
    """
    TEMP auth dependency (Phase 3).
    Expects X-User-Id header from frontend.
    """

    if not x_user_id:
        raise HTTPException(status_code=401, detail="Missing user id")

    cursor = db.execute(
        "SELECT * FROM users WHERE user_id = ?",
        (x_user_id,),
    )
    user = cursor.fetchone()

    if not user:
        raise HTTPException(status_code=401, detail="Invalid user")

    return dict(user)
