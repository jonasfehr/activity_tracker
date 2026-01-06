from bucket import Bucket, bucket_start
from input_tracker import is_active
from window_tracker import get_active_target
from datetime import datetime, timedelta
from database import insert_block
from config import BUCKET_MINUTES
try:
    from tabListener import active_tabs
except Exception:
    active_tabs = {}

current_bucket = None

def process_tab_activity():
    global current_bucket
    now = datetime.now()
    b_start = bucket_start(now)

    # Überprüfe, ob ein neues Bucket begonnen hat
    if not current_bucket or current_bucket.start != b_start:
        if current_bucket:
            # Verarbeite vorheriges Bucket (speichern)
            title = current_bucket.winner()
            if title:
                insert_block(current_bucket.start.isoformat(), (current_bucket.start + timedelta(minutes=BUCKET_MINUTES)).isoformat(), title)
        current_bucket = Bucket(b_start)

    # Tabs einfügen
    if active_tabs:
        for timestamp, tab in active_tabs.items():
            title = tab["title"]
            current_bucket.add(title)

    # Testen, ob eine Programmaktivität vorhanden ist
    if is_active():
        title = get_active_target()
        if title:
            current_bucket.add(title)