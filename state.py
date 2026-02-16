import aiosqlite
import logging

log = logging.getLogger("state")

DB_PATH = "friend_requests.db"


async def init_db(path=None):
    db = await aiosqlite.connect(path or DB_PATH)
    await db.execute("""
        CREATE TABLE IF NOT EXISTS friend_requests (
            user_id INTEGER PRIMARY KEY,
            username TEXT,
            status TEXT NOT NULL,
            error_detail TEXT,
            captcha_required INTEGER DEFAULT 0,
            requested_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    await db.commit()
    return db


async def already_requested(db, user_id):
    cursor = await db.execute(
        "SELECT 1 FROM friend_requests WHERE user_id = ?", (user_id,)
    )
    return await cursor.fetchone() is not None


async def mark_requested(db, user_id, username, status, *, detail=None, captcha=False):
    await db.execute(
        """INSERT INTO friend_requests (user_id, username, status, error_detail, captcha_required)
           VALUES (?, ?, ?, ?, ?)
           ON CONFLICT(user_id) DO UPDATE SET
               status = excluded.status,
               error_detail = excluded.error_detail,
               captcha_required = excluded.captcha_required,
               requested_at = CURRENT_TIMESTAMP""",
        (user_id, username, status, detail, int(captcha)),
    )
    await db.commit()


async def get_stats(db):
    cursor = await db.execute(
        "SELECT status, COUNT(*) FROM friend_requests GROUP BY status"
    )
    return dict(await cursor.fetchall())


async def get_total_requested(db):
    cursor = await db.execute("SELECT COUNT(*) FROM friend_requests")
    row = await cursor.fetchone()
    return row[0] if row else 0


async def get_captcha_stats(db):
    """how many requests triggered captchas vs went clean"""
    cursor = await db.execute(
        "SELECT captcha_required, COUNT(*) FROM friend_requests GROUP BY captcha_required"
    )
    rows = dict(await cursor.fetchall())
    return {
        "clean": rows.get(0, 0),
        "captcha": rows.get(1, 0),
    }
