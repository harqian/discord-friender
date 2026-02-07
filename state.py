import aiosqlite

DB_PATH = "friender.db"

CREATE_TABLE = """
CREATE TABLE IF NOT EXISTS friend_requests (
    user_id   TEXT PRIMARY KEY,
    username  TEXT,
    status    TEXT,
    requested_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
)
"""


async def init_db():
    db = await aiosqlite.connect(DB_PATH)
    await db.execute(CREATE_TABLE)
    await db.commit()
    return db


async def already_requested(db, user_id):
    cursor = await db.execute(
        "SELECT 1 FROM friend_requests WHERE user_id = ?", (str(user_id),)
    )
    return await cursor.fetchone() is not None


async def mark_requested(db, user_id, username, status):
    await db.execute(
        "INSERT OR REPLACE INTO friend_requests (user_id, username, status) VALUES (?, ?, ?)",
        (str(user_id), username, status),
    )
    await db.commit()


async def get_stats(db):
    """returns dict of status -> count"""
    cursor = await db.execute(
        "SELECT status, COUNT(*) FROM friend_requests GROUP BY status"
    )
    rows = await cursor.fetchall()
    return {row[0]: row[1] for row in rows}


async def get_total_requested(db):
    cursor = await db.execute("SELECT COUNT(*) FROM friend_requests")
    row = await cursor.fetchone()
    return row[0]
