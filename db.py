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
            seen_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    # Keyingi siklda qayerdan davom etish uchun checkpoint
    c.execute("""
        CREATE TABLE IF NOT EXISTS checkpoint (
            key TEXT PRIMARY KEY,
            value TEXT
        )
    """)
    conn.commit()
    conn.close()


def is_seen(post_id: str) -> bool:
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("SELECT 1 FROM seen_posts WHERE id=?", (post_id,))
    result = c.fetchone()
    conn.close()
    return result is not None


def mark_seen(post_id: str, title: str, price: str, region: str, url: str):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute(
        "INSERT OR IGNORE INTO seen_posts (id, title, price, region, url) VALUES (?,?,?,?,?)",
        (post_id, title, price, region, url),
    )
    conn.commit()
    conn.close()


def mark_seen_batch(posts: list):
    """Ko'p postni bir vaqtda saqlash (tezroq)."""
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.executemany(
        "INSERT OR IGNORE INTO seen_posts (id, title, price, region, url) VALUES (?,?,?,?,?)",
        [(p["id"], p["title"], p["price"], p["region"], p["url"]) for p in posts],
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


def save_checkpoint(region_index: int):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute(
        "INSERT OR REPLACE INTO checkpoint (key, value) VALUES ('region_index', ?)",
        (str(region_index),),
    )
    conn.commit()
    conn.close()


def load_checkpoint() -> int:
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("SELECT value FROM checkpoint WHERE key='region_index'")
    row = c.fetchone()
    conn.close()
    return int(row[0]) if row else 0
