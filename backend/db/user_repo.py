import uuid
from typing import Optional, Dict
from db.database import get_pool


def _new_id() -> str:
    return str(uuid.uuid4())


async def create_user(email: str, username: str, password_hash: str) -> Dict:
    """Inserts a new user. Raises asyncpg.UniqueViolationError if email/username taken."""
    user_id = _new_id()
    async with get_pool().acquire() as conn:
        row = await conn.fetchrow(
            """
            INSERT INTO users (user_id, email, username, password_hash)
            VALUES ($1, $2, $3, $4)
            RETURNING user_id, email, username, created_at
            """,
            user_id, email.lower().strip(), username.strip(), password_hash,
        )
    return dict(row)


async def get_user_by_email(email: str) -> Optional[Dict]:
    async with get_pool().acquire() as conn:
        row = await conn.fetchrow(
            "SELECT * FROM users WHERE email = $1", email.lower().strip()
        )
    return dict(row) if row else None


async def get_user_by_id(user_id: str) -> Optional[Dict]:
    async with get_pool().acquire() as conn:
        row = await conn.fetchrow(
            "SELECT user_id, email, username, created_at FROM users WHERE user_id = $1",
            user_id,
        )
    return dict(row) if row else None