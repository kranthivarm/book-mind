import asyncpg
from fastapi import APIRouter, HTTPException, status, Depends, Cookie
from fastapi.responses import JSONResponse
from pydantic import BaseModel, EmailStr, Field
from typing import Optional

from auth.jwt_handler import (
    hash_password, verify_password,
    decode_refresh_token, set_auth_cookies, clear_auth_cookies
)
from auth.dependencies import get_current_user
from db import user_repo
import logging

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/auth", tags=["Auth"])



class RegisterRequest(BaseModel):
    email:    EmailStr
    username: str = Field(..., min_length=3, max_length=30)
    password: str = Field(..., min_length=8, description="Min 8 characters")


class LoginRequest(BaseModel):
    email:    EmailStr
    password: str



@router.post("/register", status_code=status.HTTP_201_CREATED)
async def register(body: RegisterRequest):
    """
    Creates a new user account and sets auth cookies.
    Returns user info (no password).
    """
    password_hash = hash_password(body.password)

    try:
        user = await user_repo.create_user(
            email=body.email,
            username=body.username,
            password_hash=password_hash,
        )
    except asyncpg.UniqueViolationError as e:
        # Check which field is duplicate
        detail = "Email already registered." if "email" in str(e) else "Username already taken."
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=detail)

    logger.info(f"New user registered: {user['email']}")

    # Set cookies and return user info
    response = JSONResponse(
        content={
            "user_id":  user["user_id"],
            "email":    user["email"],
            "username": user["username"],
        },
        status_code=201,
    )
    set_auth_cookies(response, user["user_id"])
    return response


@router.post("/login")
async def login(body: LoginRequest):
    user = await user_repo.get_user_by_email(body.email)

    # Always run verify_password even if user not found
    # (prevents timing-based email enumeration attacks)
    # Wrap in try/except — if dummy hash is malformed it should not crash
    password_ok = False
    try:
        check_hash = user["password_hash"] if user else "$2b$12$KIX/rLfYyMfh0OqBRBqvKuqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqq"
        password_ok = verify_password(body.password, check_hash)
    except Exception:
        password_ok = False

    if not user or not password_ok:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password.",
        )

    logger.info(f"User logged in: {user['email']}")

    response = JSONResponse(content={
        "user_id":  user["user_id"],
        "email":    user["email"],
        "username": user["username"],
    })
    set_auth_cookies(response, user["user_id"])
    return response


@router.post("/logout")
async def logout():
    """Clears auth cookies — user is logged out."""
    response = JSONResponse(content={"message": "Logged out successfully."})
    clear_auth_cookies(response)
    return response


@router.post("/refresh")
async def refresh_token(
    refresh_token: Optional[str] = Cookie(default=None)  # ← read from cookie, not query param
):
    """
    Issues a new access token using the refresh token cookie.
    Called automatically by frontend when access token expires (401 response).
    """
    if not refresh_token:
        raise HTTPException(status_code=401, detail="No refresh token. Please log in.")

    user_id = decode_refresh_token(refresh_token)
    user    = await user_repo.get_user_by_id(user_id)
    if not user:
        raise HTTPException(status_code=401, detail="User not found.")

    response = JSONResponse(content={"message": "Token refreshed."})
    set_auth_cookies(response, user_id)
    return response


@router.get("/me")
async def get_me(current_user: dict = Depends(get_current_user)):
    """Returns the currently logged-in user's info. Used on app load."""
    return {
        "user_id":  current_user["user_id"],
        "email":    current_user["email"],
        "username": current_user["username"],
    }