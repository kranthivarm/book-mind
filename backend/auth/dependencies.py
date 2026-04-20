from fastapi import Cookie, Depends, HTTPException, status
from typing import Optional
from auth.jwt_handler import decode_access_token
from db import user_repo


async def get_current_user(access_token: Optional[str] = Cookie(default=None)) -> dict: 
    if not access_token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated. Please log in.",
        )

    # Verify JWT and extract user_id
    user_id = decode_access_token(access_token)

    # Confirm user still exists in DB
    user = await user_repo.get_user_by_id(user_id)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found. Please log in again.",
        )

    return user