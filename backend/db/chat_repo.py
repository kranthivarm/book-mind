import json
import uuid
from datetime import datetime, timezone
from typing import List, Optional, Dict, Any

from db.database import get_pool


def _new_id() -> str:
    return str(uuid.uuid4())


def _now() -> datetime:
    return datetime.now(timezone.utc)



async def create_chat(user_id: str, book_id: str, book_name: str,
                      total_pages: int, total_chunks: int) -> Dict:
    chat_id = _new_id()
    now = _now()
    async with get_pool().acquire() as conn:
        row = await conn.fetchrow(
            """
            INSERT INTO chats (chat_id, user_id, book_id, book_name, total_pages, total_chunks, created_at, last_at)
            VALUES ($1, $2, $3, $4, $5, $6, $7, $7)
            RETURNING *
            """,
            chat_id, user_id, book_id, book_name, total_pages, total_chunks, now,
        )
    return dict(row)


async def get_all_chats(user_id: str) -> List[Dict]:
    """Returns only THIS user's chats."""
    async with get_pool().acquire() as conn:
        rows = await conn.fetch(
            "SELECT * FROM chats WHERE user_id = $1 ORDER BY last_at DESC", user_id
        )
    return [dict(r) for r in rows]


async def get_chat(chat_id: str, user_id: str) -> Optional[Dict]:
    """Returns chat only if it belongs to this user."""
    async with get_pool().acquire() as conn:
        row = await conn.fetchrow(
            "SELECT * FROM chats WHERE chat_id = $1 AND user_id = $2", chat_id, user_id
        )
    return dict(row) if row else None


async def update_chat_preview(chat_id: str, last_message: str):
    async with get_pool().acquire() as conn:
        await conn.execute(
            "UPDATE chats SET last_message = $1, last_at = $2 WHERE chat_id = $3",
            last_message[:80], _now(), chat_id,
        )


async def delete_chat(chat_id: str, user_id: str):
    """Deletes chat only if it belongs to this user."""
    async with get_pool().acquire() as conn:
        await conn.execute(
            "DELETE FROM chats WHERE chat_id = $1 AND user_id = $2", chat_id, user_id
        )



async def save_message(chat_id: str, role: str, text: str,
                       sources: Optional[List[Dict]] = None) -> Dict:
    message_id = _new_id()
    async with get_pool().acquire() as conn:
        row = await conn.fetchrow(
            """
            INSERT INTO messages (message_id, chat_id, role, text, sources, created_at)
            VALUES ($1, $2, $3, $4, $5, $6)
            RETURNING *
            """,
            message_id, chat_id, role, text,
            json.dumps(sources) if sources else None, _now(),
        )
    return _fmt(dict(row))


async def get_messages(chat_id: str) -> List[Dict]:
    async with get_pool().acquire() as conn:
        rows = await conn.fetch(
            "SELECT * FROM messages WHERE chat_id = $1 ORDER BY created_at ASC", chat_id
        )
    return [_fmt(dict(r)) for r in rows]


async def update_message(message_id: str, text: str, sources: Optional[List[Dict]] = None):
    async with get_pool().acquire() as conn:
        await conn.execute(
            "UPDATE messages SET text = $1, sources = $2 WHERE message_id = $3",
            text, json.dumps(sources) if sources else None, message_id,
        )


def _fmt(row: Dict) -> Dict:
    if row.get("sources") and isinstance(row["sources"], str):
        try:
            row["sources"] = json.loads(row["sources"])
        except Exception:
            row["sources"] = None
    return row