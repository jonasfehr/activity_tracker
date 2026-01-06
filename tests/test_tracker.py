import unittest
import tempfile
import os
import importlib
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import config

class TrackerTabTests(unittest.TestCase):
    def setUp(self):
        fd, path = tempfile.mkstemp(suffix='.db')
        os.close(fd)
        self.db_path = path
        config.DB_PATH = self.db_path
        # reload modules to pick up new DB path
        import database
        importlib.reload(database)
        # reload tabListener and tracker so active_tabs is fresh
        import tabListener
        importlib.reload(tabListener)
        import tracker
        importlib.reload(tracker)
        self.tabListener = tabListener
        self.tracker = tracker

    def tearDown(self):
        try:
            os.remove(self.db_path)
        except Exception:
            pass

    def test_tab_dedup_and_clear(self):
        from datetime import datetime, timedelta
        now = datetime.now()
        # Simulate multiple pings for the same URL (should keep only latest)
        url = 'http://example.test'
        self.tabListener.active_tabs[url] = {'title': 'DemoTab', 'url': url, 'ts': now - timedelta(seconds=30)}
        # Second (later) ping should overwrite
        self.tabListener.active_tabs[url] = {'title': 'DemoTab', 'url': url, 'ts': now}

        # Ensure the active window appears to be Firefox so tracker processes tabs
        # Ensure tracker sees an active Firefox window by patching the function
        # that tracker calls (get_active_target) directly.
        self.tracker.get_active_target = lambda: 'Firefox'
        # Run processing
        self.tracker.process_tab_activity()

        # Now query DB and ensure only one row exists for this tab title
        import sqlite3
        con = sqlite3.connect(self.db_path)
        cur = con.cursor()
        rows = cur.execute("SELECT id,start,end,title FROM blocks WHERE title LIKE ?", (f"DemoTab%",)).fetchall()
        self.assertEqual(len(rows), 1)

        # active_tabs should be cleared
        self.assertEqual(len(self.tabListener.active_tabs), 0)

    def test_receive_tab_only_when_firefox_active(self):
        """The HTTP endpoint should only store a tab when Firefox is active."""
        class DummyReq:
            def __init__(self, payload):
                self._payload = payload
            async def json(self):
                return self._payload

        url = 'http://example.test'
        payload = {'title': 'RecvTab', 'url': url}

        # Case 1: window_tracker reports Firefox active
        import window_tracker
        window_tracker.get_active_target = lambda: 'Firefox'
        # call the handler
        import asyncio
        res = asyncio.get_event_loop().run_until_complete(self.tabListener.receive_tab(DummyReq(payload)))
        self.assertEqual(res.get('status'), 'ok')
        self.assertIn(url, self.tabListener.active_tabs)
        # clear
        self.tabListener.active_tabs.clear()

        # Case 2: not Firefox
        window_tracker.get_active_target = lambda: 'SomeOtherApp'
        res2 = asyncio.get_event_loop().run_until_complete(self.tabListener.receive_tab(DummyReq(payload)))
        self.assertEqual(res2.get('status'), 'ignored')
        self.assertNotIn(url, self.tabListener.active_tabs)

if __name__ == '__main__':
    unittest.main()
