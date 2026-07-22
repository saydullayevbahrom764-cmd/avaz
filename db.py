import sqlite3
from config import DB_PATH


def init_db():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("""
        CREATE TABLE IF NOT EXISTS seen_posts (
            id TEXT PRIMARY KEY,
            title TEXT,
            price TEXT,
            region TEXT,
            url TEXT,
            sent INTEGER DEFAULT 0,
            seen_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    conn.commit()
    conn.close()


def is_seen(post_id: str) -> bool:
    """Post avval ko'rilganmi?"""
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("SELECT 1 FROM seen_posts WHERE id=?", (post_id,))
    result = c.fetchone()
    conn.close()
    return result is not None


def mark_seen(post_id: str, title: str, price: str, region: str, url: str):
    """Post yuborildi va ko'rildi deb belgilash."""
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute(
        "INSERT OR IGNORE INTO seen_posts (id, title, price, region, url, sent) VALUES (?,?,?,?,?,1)",
        (post_id, title, price, region, url),
    )
    conn.commit()
    conn.close()


def mark_seen_no_send(post_id: str, title: str, price: str, region: str, url: str):
    """Post ko'rildi lekin yuborilmadi deb belgilash (birinchi skan)."""
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute(
        "INSERT OR IGNORE INTO seen_posts (id, title, price, region, url, sent) VALUES (?,?,?,?,?,0)",
        (post_id, title, price, region, url),
    )
    conn.commit()
    conn.close()


def get_seen_count() -> int:
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("SELECT COUNT(*) FROM seen_posts")
    count = c.fetchone()[0]
    conn.close()
    return count


def get_sent_count() -> int:
    """Yuborilgan postlar soni."""
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("SELECT COUNT(*) FROM seen_posts WHERE sent=1")
    count = c.fetchone()[0]
    conn.close()
    return count
