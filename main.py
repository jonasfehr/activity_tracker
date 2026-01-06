import threading
import uvicorn
from tabListener import run_listener
from tracker import run_periodic
from config import TRACK_INTERVAL_SECONDS


def main():
    # Start tab listener in background thread
    t1 = threading.Thread(target=run_listener, daemon=True)
    t1.start()

    # Start tracker loop in background thread
    t2 = threading.Thread(target=lambda: run_periodic(TRACK_INTERVAL_SECONDS), daemon=True)
    t2.start()

    # Run web UI (blocking)
    uvicorn.run("webui:app", host="127.0.0.1", port=9432)


if __name__ == "__main__":
    main()