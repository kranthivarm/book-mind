# routers/auth.py
import asyncpg
from fastapi import APIRouter, HTTPException, status, Depends
from fastapi.responses import JSONResponse
from pydantic import BaseModel, EmailStr, Field
from typing import Optional

from auth.jwt_handler import (
    hash_password, verify_password,
    create_access_token, create_refresh_token,
    decode_refresh_token,
)
from auth.dependencies import get_current_user
from db import user_repo
import logging

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/auth", tags=["Auth"])


class RegisterRequest(BaseModel):
    email:    EmailStr
    username: str = Field(..., min_length=3, max_length=30)
    password: str = Field(..., min_length=8)


class LoginRequest(BaseModel):
    email:    EmailStr
    password: str


class RefreshRequest(BaseModel):
    refresh_token: str


def _token_response(user: dict) -> dict:
    """
    Returns tokens in the JSON body.
    Frontend stores them in memory (React state) — no cookies needed.
    Tokens are sent as Authorization: Bearer <token> on every request.
    """
    return {
        "access_token":  create_access_token(user["user_id"]),
        "refresh_token": create_refresh_token(user["user_id"]),
        "token_type":    "bearer",
        "user": {
            "user_id":  user["user_id"],
            "email":    user["email"],
            "username": user["username"],
        }
    }


@router.post("/register", status_code=status.HTTP_201_CREATED)
async def register(body: RegisterRequest):
    password_hash = hash_password(body.password)
    try:
        user = await user_repo.create_user(
            email=body.email,
            username=body.username,
            password_hash=password_hash,
        )
    except asyncpg.UniqueViolationError as e:
        detail = "Email already registered." if "email" in str(e) else "Username already taken."
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=detail)

    logger.info(f"New user registered: {user['email']}")
    return _token_response(user)


@router.post("/login")
async def login(body: LoginRequest):
    user = await user_repo.get_user_by_email(body.email)

    password_ok = False
    try:
        check_hash = user["password_hash"] if user else "$2b$12$KIX/rLfYyMfh0OqBRBqvKuqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqq"
        password_ok = verify_password(body.password, check_hash)
    except Exception:
        password_ok = False

    if not user or not password_ok:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Incorrect email or password.")

    logger.info(f"User logged in: {user['email']}")
    return _token_response(user)


@router.post("/refresh")
async def refresh_token(body: RefreshRequest):
    """
    Takes refresh_token from request body (not cookie).
    Returns a new access_token.
    """
    user_id = decode_refresh_token(body.refresh_token)
    user    = await user_repo.get_user_by_id(user_id)
    if not user:
        raise HTTPException(status_code=401, detail="User not found.")

    return {
        "access_token":  create_access_token(user_id),
        "refresh_token": body.refresh_token,   # same refresh token
        "token_type":    "bearer",
    }


@router.post("/logout")
async def logout():
    # With Bearer tokens, logout is handled client-side
    # (frontend just deletes tokens from memory/localStorage)
    return {"message": "Logged out successfully."}


@router.get("/me")
async def get_me(current_user: dict = Depends(get_current_user)):
    return {
        "user_id":  current_user["user_id"],
        "email":    current_user["email"],
        "username": current_user["username"],
    }