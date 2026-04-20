from datetime import datetime, timedelta, timezone
from typing import Optional

from jose import JWTError, jwt
from passlib.context import CryptContext
from fastapi import Cookie, HTTPException, status
from fastapi.responses import Response

from config import settings

# bcrypt hasher — rounds=12 is the standard for production
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


# ── Password ───────────────────────────────────────────────────────────────────

def hash_password(plain: str) -> str:
    return pwd_context.hash(plain)


def verify_password(plain: str, hashed: str) -> bool:
    return pwd_context.verify(plain, hashed)


# ── Token creation ─────────────────────────────────────────────────────────────

def create_access_token(user_id: str) -> str:
    """
    Creates a JWT access token.
    Payload: { sub: user_id, type: "access", exp: now + 15min }
    Signed with SECRET_KEY using HS256 algorithm.
    """
    expire = datetime.now(timezone.utc) + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    payload = {"sub": user_id, "type": "access", "exp": expire}
    return jwt.encode(payload, settings.SECRET_KEY, algorithm=settings.JWT_ALGORITHM)


def create_refresh_token(user_id: str) -> str:
    """
    Creates a JWT refresh token.
    Longer expiry — used only to issue new access tokens.
    """
    expire = datetime.now(timezone.utc) + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)
    payload = {"sub": user_id, "type": "refresh", "exp": expire}
    return jwt.encode(payload, settings.SECRET_KEY, algorithm=settings.JWT_ALGORITHM)


# ── Token verification ─────────────────────────────────────────────────────────

def decode_access_token(token: str) -> str:
    """
    Decodes and validates an access token.
    Returns user_id (the 'sub' claim).
    Raises HTTPException 401 if invalid/expired.
    """
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.JWT_ALGORITHM])
        if payload.get("type") != "access":
            raise HTTPException(status_code=401, detail="Invalid token type")
        user_id: str = payload.get("sub")
        if not user_id:
            raise HTTPException(status_code=401, detail="Invalid token")
        return user_id
    except JWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token expired or invalid. Please log in again.",
        )


def decode_refresh_token(token: str) -> str:
    """Decodes refresh token. Returns user_id."""
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.JWT_ALGORITHM])
        if payload.get("type") != "refresh":
            raise HTTPException(status_code=401, detail="Invalid token type")
        user_id: str = payload.get("sub")
        if not user_id:
            raise HTTPException(status_code=401, detail="Invalid token")
        return user_id
    except JWTError:
        raise HTTPException(status_code=401, detail="Refresh token expired. Please log in again.")


# ── Cookie helpers ─────────────────────────────────────────────────────────────

def set_auth_cookies(response: Response, user_id: str):
    """
    Sets both tokens as httpOnly cookies on the response.
    Call this after login or registration.
    """
    access_token  = create_access_token(user_id)
    refresh_token = create_refresh_token(user_id)

    # Access token cookie
    response.set_cookie(
        key="access_token",
        value=access_token,
        httponly=True,                              # JS cannot read this
        secure=settings.COOKIE_SECURE,             # True in prod (HTTPS only)
        samesite="lax",
        max_age=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
    )

    # Refresh token cookie
    response.set_cookie(
        key="refresh_token",
        value=refresh_token,
        httponly=True,
        secure=settings.COOKIE_SECURE,
        samesite="lax",
        max_age=settings.REFRESH_TOKEN_EXPIRE_DAYS * 24 * 60 * 60,
    )


def clear_auth_cookies(response: Response):
    """Clears both cookies — call on logout."""
    response.delete_cookie("access_token")
    response.delete_cookie("refresh_token")