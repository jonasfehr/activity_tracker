import unittest
import tempfile
import os
import importlib
import sys
from pathlib import Path
# ensure project root is on sys.path so tests can import project modules
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import config

class DatabaseMergeTests(unittest.TestCase):
    def setUp(self):
        # Create a temp DB file
        fd, path = tempfile.mkstemp(suffix='.db')
        os.close(fd)
        self.db_path = path
        # Point config to the temp DB and reload database module
        config.DB_PATH = self.db_path
        import database
        importlib.reload(database)
        self.db = database

    def tearDown(self):
        try:
            os.remove(self.db_path)
        except Exception:
            pass

    def test_merge_adjacent_blocks(self):
        from datetime import datetime, timedelta
        now = datetime.now()
        self.db.insert_block(now, now + timedelta(seconds=10), 'MergeTest')
        # Adjacent (end == start) -> should merge
        self.db.insert_block(now + timedelta(seconds=10), now + timedelta(seconds=20), 'MergeTest')
        rows = self._rows('MergeTest')
        self.assertEqual(len(rows), 1)
        # end should be extended to 20s
        self.assertTrue(rows[0][2].startswith((now + timedelta(seconds=20)).isoformat()[:19]))

    def test_no_merge_gap(self):
        from datetime import datetime, timedelta
        now = datetime.now()
        # Use a gap larger than the configured MERGE_GAP_SECONDS to ensure no merge
        gap = max(6, getattr(__import__('config'), 'MERGE_GAP_SECONDS') + 1)
        self.db.insert_block(now, now + timedelta(seconds=10), 'GapTest')
        self.db.insert_block(now + timedelta(seconds=10 + gap), now + timedelta(seconds=20 + gap), 'GapTest')
        rows = self._rows('GapTest')
        self.assertEqual(len(rows), 2)

    def test_merge_at_threshold(self):
        from datetime import datetime, timedelta
        now = datetime.now()
        gap = getattr(__import__('config'), 'MERGE_GAP_SECONDS')
        self.db.insert_block(now, now + timedelta(seconds=10), 'ThresholdTest')
        # Start exactly at end + gap -> should merge
        self.db.insert_block(now + timedelta(seconds=10 + gap), now + timedelta(seconds=20 + gap), 'ThresholdTest')
        rows = self._rows('ThresholdTest')
        self.assertEqual(len(rows), 1)
    def test_insert_tab_block(self):
        from datetime import datetime
        now = datetime.now()
        self.db.insert_tab_block(now, 'TabTitle', 'http://example.com')
        rows = self._rows('TabTitle - http://example.com')
        self.assertEqual(len(rows), 1)

    def _rows(self, title_like):
        import sqlite3
        con = sqlite3.connect(self.db_path)
        cur = con.cursor()
        rows = cur.execute("SELECT id,start,end,title FROM blocks WHERE title LIKE ? ORDER BY id", (f"{title_like}%",)).fetchall()
        return rows

if __name__ == '__main__':
    unittest.main()
