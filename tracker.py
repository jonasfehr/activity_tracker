from database import insert_tab_block, insert_block
from datetime import datetime, timedelta
from bucket import Bucket, bucket_start
try:
    from tabListener import active_tabs
except Exception:
    # tabListener (FastAPI) may not be available at import time in some contexts
    active_tabs = {}
from input_tracker import is_active
from window_tracker import get_active_target
from config import TRACK_INTERVAL_SECONDS, BUCKET_MINUTES
import time

current_bucket = None

def process_tab_activity():
    global current_bucket
    now = datetime.now()
    b_start = bucket_start(now)

    if not current_bucket or current_bucket.start != b_start:
        if current_bucket:
            # Verarbeite vorheriges Bucket (speichern)
            title = current_bucket.winner()
            if title:
                insert_block(current_bucket.start.isoformat(), (current_bucket.start + timedelta(minutes=BUCKET_MINUTES)).isoformat(), title)
        current_bucket = Bucket(b_start)

    # Nur Tabs verwenden, wenn der aktive Prozess Firefox ist
    # Handle different return types defensively (string, None, even callables)
    active_window = None
    try:
        aw = get_active_target
        # If get_active_target is callable, call it to get the current window title
        if callable(aw):
            active_window = aw()
        else:
            active_window = aw
    except Exception:
        active_window = None

    active_window_str = str(active_window) if active_window is not None else ""
    is_firefox = ("firefox" in active_window_str.lower()) or ("mozilla" in active_window_str.lower())

    if is_firefox and active_tabs:
        # active_tabs is keyed by URL and stores the latest seen timestamp under 'ts'.
        # Process the current snapshot (one entry per URL), then clear the store
        # to avoid re-inserting the same entries on subsequent ticks.
        for tab in list(active_tabs.values()):
            title = tab.get("title")
            url = tab.get("url")
            ts = tab.get("ts") or datetime.now()
            # Insert a tab block using the recorded timestamp
            insert_tab_block(ts, title, url)
            current_bucket.add(title)
        # Clear processed entries
        try:
            active_tabs.clear()
        except Exception:
            for k in list(active_tabs.keys()):
                active_tabs.pop(k, None)
    else:
        # Testen, ob eine Programmaktivität vorhanden ist und kein Firefox aktiv ist
        if is_active():
            title = active_window_str or get_active_target()
            if title:
                current_bucket.add(title)

def run_periodic(interval_seconds=TRACK_INTERVAL_SECONDS):
    while True:
        process_tab_activity()
        time.sleep(interval_seconds)

if __name__ == "__main__":
    run_periodic()
