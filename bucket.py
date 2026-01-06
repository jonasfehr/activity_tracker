from datetime import datetime, timedelta
from config import BUCKET_MINUTES

class Bucket:
    def __init__(self, start: datetime):
        self.start = start
        self.counts = {}

    def add(self, title: str):
        if not title:
            return
        self.counts[title] = self.counts.get(title, 0) + 1

    def winner(self):
        if not self.counts:
            return None
        return max(self.counts.items(), key=lambda x: x[1])[0]


def bucket_start(now: datetime):
    """Return the start time of the bucket containing `now`.

    The bucket size is configurable via `config.BUCKET_MINUTES`.
    """
    minute = (now.minute // BUCKET_MINUTES) * BUCKET_MINUTES
    return datetime(now.year, now.month, now.day, now.hour, minute)
