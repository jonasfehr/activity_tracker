# Configuration for activity tracker
# Intervall in Sekunden in dem die Tabs / aktive Fenster abgefragt werden
TRACK_INTERVAL_SECONDS = 5

# Größe eines Buckets in Minuten (z.B. 5 für 5-Minuten-Buckets)
BUCKET_MINUTES = 5
# Merge gap in seconds: if two blocks with the same title are closer than or equal
# to this gap, they will be merged into a single block (default: 5 seconds).
MERGE_GAP_SECONDS = 5
# Interval für das Browser-Plugin (ms)
TAB_SEND_INTERVAL_MS = 10000

# Pfad zur SQLite Datenbank (optional)
DB_PATH = "activity.db"