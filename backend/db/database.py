import asyncpg
from Config import settings
import logging

logger = logging.getLogger(__name__)

# Global pool 
_pool: asyncpg.Pool = None


async def init_db():
    global _pool

    logger.info("Connecting to PostgreSQL…")
    _pool = await asyncpg.create_pool(
        dsn=settings.DATABASE_URL,
        min_size=2,    # always keep 2 connections ready
        max_size=10,   # max 10 concurrent connections
        command_timeout=30,
    )
    logger.info("PostgreSQL pool created")

    # Create tables if they don't exist
    await _create_tables()
    logger.info("Database tables ready")


async def close_db():
    global _pool
    if _pool:
        await _pool.close()
        logger.info("PostgreSQL pool closed")


def get_pool() -> asyncpg.Pool:
    return _pool


async def _create_tables():
    async with _pool.acquire() as conn:
        await conn.execute("""
            CREATE TABLE IF NOT EXISTS chats (
                chat_id      TEXT PRIMARY KEY,
                book_id      TEXT        NOT NULL,
                book_name    TEXT        NOT NULL,
                total_pages  INTEGER     NOT NULL DEFAULT 0,
                total_chunks INTEGER     NOT NULL DEFAULT 0,
                created_at   TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                last_message TEXT        NOT NULL DEFAULT '',
                last_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
            );

            CREATE TABLE IF NOT EXISTS messages (
                message_id  TEXT PRIMARY KEY,
                chat_id     TEXT        NOT NULL REFERENCES chats(chat_id) ON DELETE CASCADE,
                role        TEXT        NOT NULL CHECK (role IN ('user', 'ai')),
                text        TEXT        NOT NULL DEFAULT '',
                sources     JSONB,
                created_at  TIMESTAMPTZ NOT NULL DEFAULT NOW()
            );

            CREATE INDEX IF NOT EXISTS idx_messages_chat_id
                ON messages(chat_id, created_at);

            CREATE INDEX IF NOT EXISTS idx_chats_last_at
                ON chats(last_at DESC);
        """)