from typing import Any

import asyncpg

_pool: asyncpg.Pool | None = None


async def init_db(database_url: str) -> None:
    global _pool
    _pool = await asyncpg.create_pool(database_url, min_size=1, max_size=5, command_timeout=30)
    async with _pool.acquire() as conn:
        await conn.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id BIGSERIAL PRIMARY KEY,
            telegram_id BIGINT UNIQUE NOT NULL,
            username TEXT,
            first_name TEXT,
            plan TEXT NOT NULL DEFAULT 'free',
            premium_until TIMESTAMPTZ,
            digest_enabled BOOLEAN NOT NULL DEFAULT TRUE,
            digest_hour INTEGER NOT NULL DEFAULT 9,
            timezone TEXT NOT NULL DEFAULT 'Europe/Moscow',
            created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
        );
        ALTER TABLE users ADD COLUMN IF NOT EXISTS premium_until TIMESTAMPTZ;
        ALTER TABLE users ADD COLUMN IF NOT EXISTS digest_hour INTEGER NOT NULL DEFAULT 9;
        ALTER TABLE users ADD COLUMN IF NOT EXISTS timezone TEXT NOT NULL DEFAULT 'Europe/Moscow';

        CREATE TABLE IF NOT EXISTS topics (
            id BIGSERIAL PRIMARY KEY,
            user_id BIGINT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
            name TEXT NOT NULL,
            slug TEXT NOT NULL,
            created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            UNIQUE(user_id, slug)
        );

        CREATE TABLE IF NOT EXISTS feedback (
            id BIGSERIAL PRIMARY KEY,
            user_id BIGINT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
            item_key TEXT NOT NULL,
            value SMALLINT NOT NULL CHECK (value IN (-1, 1)),
            created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            UNIQUE(user_id, item_key)
        );

        CREATE TABLE IF NOT EXISTS items (
            id BIGSERIAL PRIMARY KEY,
            item_key TEXT UNIQUE NOT NULL,
            title TEXT NOT NULL,
            summary TEXT NOT NULL,
            url TEXT NOT NULL,
            source TEXT NOT NULL,
            published_at TIMESTAMPTZ,
            topics TEXT[] NOT NULL DEFAULT '{}',
            created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
        );

        CREATE TABLE IF NOT EXISTS deliveries (
            id BIGSERIAL PRIMARY KEY,
            user_id BIGINT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
            item_id BIGINT NOT NULL REFERENCES items(id) ON DELETE CASCADE,
            delivered_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            UNIQUE(user_id, item_id)
        );
        CREATE INDEX IF NOT EXISTS idx_items_published ON items(published_at DESC);
        CREATE INDEX IF NOT EXISTS idx_deliveries_user ON deliveries(user_id);
        """)


def pool() -> asyncpg.Pool:
    if _pool is None:
        raise RuntimeError("Database is not initialized")
    return _pool


async def close() -> None:
    global _pool
    if _pool:
        await _pool.close()
        _pool = None


async def upsert_user(telegram_id: int, username: str | None, first_name: str | None) -> dict[str, Any]:
    row = await pool().fetchrow("""
        INSERT INTO users (telegram_id, username, first_name)
        VALUES ($1, $2, $3)
        ON CONFLICT (telegram_id) DO UPDATE SET
            username=EXCLUDED.username,
            first_name=EXCLUDED.first_name,
            updated_at=NOW()
        RETURNING *
    """, telegram_id, username, first_name)
    return dict(row)


async def get_user(telegram_id: int) -> dict[str, Any] | None:
    row = await pool().fetchrow("SELECT * FROM users WHERE telegram_id=$1", telegram_id)
    return dict(row) if row else None


async def add_topic(telegram_id: int, name: str, slug: str) -> bool:
    user = await pool().fetchrow("SELECT id FROM users WHERE telegram_id=$1", telegram_id)
    if not user:
        return False
    try:
        await pool().execute("INSERT INTO topics(user_id,name,slug) VALUES($1,$2,$3)", user["id"], name, slug)
        return True
    except asyncpg.UniqueViolationError:
        return False


async def remove_topic(telegram_id: int, slug: str) -> None:
    await pool().execute("""
        DELETE FROM topics
        WHERE user_id=(SELECT id FROM users WHERE telegram_id=$1) AND slug=$2
    """, telegram_id, slug)


async def get_topics(telegram_id: int) -> list[dict[str, Any]]:
    rows = await pool().fetch("""
        SELECT t.* FROM topics t JOIN users u ON u.id=t.user_id
        WHERE u.telegram_id=$1 ORDER BY t.created_at
    """, telegram_id)
    return [dict(r) for r in rows]


async def count_topics(telegram_id: int) -> int:
    return await pool().fetchval("""
        SELECT COUNT(*) FROM topics t JOIN users u ON u.id=t.user_id WHERE u.telegram_id=$1
    """, telegram_id)


async def set_digest(telegram_id: int, enabled: bool) -> None:
    await pool().execute("UPDATE users SET digest_enabled=$2, updated_at=NOW() WHERE telegram_id=$1", telegram_id, enabled)


async def set_digest_hour(telegram_id: int, hour: int) -> None:
    await pool().execute("UPDATE users SET digest_hour=$2, updated_at=NOW() WHERE telegram_id=$1", telegram_id, hour)


async def set_premium(telegram_id: int, until) -> None:
    await pool().execute("UPDATE users SET plan='premium', premium_until=$2, updated_at=NOW() WHERE telegram_id=$1", telegram_id, until)


async def save_item(item: dict[str, Any]) -> int:
    row = await pool().fetchrow("""
        INSERT INTO items(item_key,title,summary,url,source,published_at,topics)
        VALUES($1,$2,$3,$4,$5,$6,$7)
        ON CONFLICT(item_key) DO UPDATE SET
            title=EXCLUDED.title, summary=EXCLUDED.summary, url=EXCLUDED.url,
            source=EXCLUDED.source, published_at=EXCLUDED.published_at, topics=EXCLUDED.topics
        RETURNING id
    """, item["item_key"], item["title"], item["summary"], item["url"], item["source"], item.get("published_at"), item.get("topics", []))
    return row["id"]


async def get_unseen_for_user(telegram_id: int, limit: int) -> list[dict[str, Any]]:
    rows = await pool().fetch("""
        SELECT i.*
        FROM items i
        JOIN users u ON u.telegram_id=$1
        JOIN topics t ON t.user_id=u.id AND t.slug=ANY(i.topics)
        LEFT JOIN feedback f ON f.user_id=u.id AND f.item_key=i.item_key
        LEFT JOIN deliveries d ON d.user_id=u.id AND d.item_id=i.id
        WHERE d.id IS NULL AND COALESCE(f.value,0) >= 0
        GROUP BY i.id
        ORDER BY i.published_at DESC NULLS LAST, i.created_at DESC
        LIMIT $2
    """, telegram_id, limit)
    return [dict(r) for r in rows]


async def mark_delivered(telegram_id: int, item_id: int) -> None:
    await pool().execute("""
        INSERT INTO deliveries(user_id,item_id)
        SELECT id,$2 FROM users WHERE telegram_id=$1
        ON CONFLICT DO NOTHING
    """, telegram_id, item_id)


async def set_feedback(telegram_id: int, item_key: str, value: int) -> None:
    await pool().execute("""
        INSERT INTO feedback(user_id,item_key,value)
        SELECT id,$2,$3 FROM users WHERE telegram_id=$1
        ON CONFLICT(user_id,item_key) DO UPDATE SET value=EXCLUDED.value, created_at=NOW()
    """, telegram_id, item_key, value)


async def get_due_digest_users(timezone_name: str, hour: int) -> list[int]:
    rows = await pool().fetch("""
        SELECT telegram_id FROM users
        WHERE digest_enabled=TRUE AND timezone=$1 AND digest_hour=$2
          AND (premium_until IS NULL OR premium_until > NOW() OR plan='free')
    """, timezone_name, hour)
    return [r["telegram_id"] for r in rows]


async def get_users() -> list[dict[str, Any]]:
    rows = await pool().fetch("SELECT telegram_id, timezone, digest_hour FROM users WHERE digest_enabled=TRUE")
    return [dict(r) for r in rows]
