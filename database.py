import sqlite3
from datetime import datetime, timedelta
import logging
from config import DB_PATH, MERGE_GAP_SECONDS

# Logging
logger = logging.getLogger(__name__)
if not logging.getLogger().handlers:
    logging.basicConfig(level=logging.INFO)

# DB connection (initialised via DB_PATH or set_db_path)
conn = None
cur = None

def _init_db(path=None):
    global conn, cur
    if conn:
        try:
            conn.close()
        except Exception:
            pass
    dbp = path or DB_PATH
    conn = sqlite3.connect(dbp, check_same_thread=False)
    cur = conn.cursor()
    # Tabelle für Blöcke, falls noch nicht vorhanden
    cur.execute("""
    CREATE TABLE IF NOT EXISTS blocks (
        id INTEGER PRIMARY KEY,
        start TEXT,
        end TEXT,
        title TEXT
    )
    """)
    conn.commit()

# initialize at import time with config DB_PATH
_init_db(DB_PATH)

from datetime import datetime, timedelta

# Funktion, um Block-Daten zu speichern
def set_db_path(path: str):
    """Set a new DB path and reinitialize the connection (for tests or runtime override)."""
    _init_db(path)
    logger.info("Database path set to %s", path)


def insert_block(start, end, title):
    """Insert a block or merge with the latest block if titles match and windows touch/overlap.

    Behavior:
    - If the latest block in DB has the same title and its end time overlaps or is within MERGE_GAP_SECONDS seconds
      of `start` (i.e., gap <= MERGE_GAP_SECONDS), update that block's end to the max of the two ends instead of inserting a new row.
    - Otherwise, insert a new block row.
    Logging: emits INFO when merging or inserting.
    """
    # Normalize to datetime objects for comparison
    def to_dt(v):
        if isinstance(v, datetime):
            return v
        try:
            return datetime.fromisoformat(str(v))
        except Exception:
            return None

    s_dt = to_dt(start)
    e_dt = to_dt(end)
    t = str(title)

    # Get latest block
    last = cur.execute("SELECT id, start, end, title FROM blocks ORDER BY id DESC LIMIT 1").fetchone()
    if last and s_dt and e_dt:
        last_id, last_s, last_e, last_t = last
        try:
            last_end_dt = datetime.fromisoformat(last_e)
        except Exception:
            last_end_dt = None

        # Merge when same title and windows overlap or are within MERGE_GAP_SECONDS
        if last_t == t and last_end_dt is not None:
            gap = (s_dt - last_end_dt).total_seconds()
            if gap <= MERGE_GAP_SECONDS:
                new_end = max(last_end_dt, e_dt)
                cur.execute("UPDATE blocks SET end = ? WHERE id = ?", (new_end.isoformat(), last_id))
                conn.commit()
                logger.info("Merged block id=%s title=%s new_end=%s (gap=%.2fs, threshold=%ss)", last_id, t, new_end.isoformat(), gap, MERGE_GAP_SECONDS)
                return

    # Fallback: insert a new row
    s = start.isoformat() if hasattr(start, "isoformat") else str(start)
    e = end.isoformat() if hasattr(end, "isoformat") else str(end)
    cur.execute("""
    INSERT INTO blocks (start, end, title)
    VALUES (?, ?, ?)
    """, (s, e, t))
    conn.commit()
    last_id = cur.lastrowid
    logger.info("Inserted block id=%s title=%s start=%s end=%s", last_id, t, s, e)

# Funktion, um Tab-Daten zu speichern (neue Funktion)
def insert_tab_block(ts, title, url):
    # Coerce ts to datetime if possible
    s_dt = ts if isinstance(ts, datetime) else None

    # Build the title we store for tabs
    t = f"{title} - {url}"

    # Treat tab events as a very short block (start == end == ts). Use insert_block's merge logic
    insert_block(s_dt or str(ts), s_dt or str(ts), t)

# Funktion, um Blöcke für einen bestimmten Tag zu holen
def get_blocks_for_day(date):
    """Return rows for the given date in chronological order.

    Uses ISO-like start prefix matching and orders by start time ascending so
    callers receive blocks in time order.
    """
    return cur.execute(
        "SELECT * FROM blocks WHERE start LIKE ? ORDER BY start ASC",
        (f"{date}%",)
    ).fetchall()


def delete_until_first_title_contains(date: str, substring: str) -> int:
    """Delete all blocks for `date` that occur before the first block whose
    title contains `substring` (case-insensitive).

    Returns the number of deleted rows. If no matching block is found, does nothing
    and returns 0.
    """
    rows = cur.execute(
        "SELECT id, start, end, title FROM blocks WHERE start LIKE ? ORDER BY start ASC",
        (f"{date}%",)
    ).fetchall()

    substring_lower = substring.lower()
    cutoff_start = None
    for r in rows:
        if r[3] and substring_lower in r[3].lower():
            cutoff_start = r[1]
            break

    if not cutoff_start:
        return 0

    # Delete rows with start strictly before the cutoff_start
    res = cur.execute(
        "DELETE FROM blocks WHERE start LIKE ? AND start < ?",
        (f"{date}%", cutoff_start)
    )
    conn.commit()
    deleted = res.rowcount if hasattr(res, 'rowcount') else None
    # SQLite in the python sqlite3 module sets rowcount to -1 for DELETE; compute count instead
    if deleted is None or deleted == -1:
        deleted = cur.execute("SELECT COUNT(*) FROM blocks WHERE start LIKE ? AND start < ?", (f"{date}%", cutoff_start)).fetchone()[0]
    logger.info("Deleted %d rows before first match '%s' on %s", deleted, substring, date)
    return deleted
