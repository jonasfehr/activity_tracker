from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
import uvicorn
from database import insert_tab_block
from datetime import datetime
from input_tracker import is_active

# Try to import the window tracker helper to determine if Firefox is active.
# If unavailable, we default to not storing incoming tabs (safer behavior).
try:
    from window_tracker import get_active_target
except Exception:
    get_active_target = None

app = FastAPI()

# Allow CORS for development (e.g. firefox extension origin). Adjust for production.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Speichere die Tabs in einer globalen Liste (oder DB)
active_tabs = {}

@app.post("/tab")
async def receive_tab(req: Request):
    data = await req.json()
    title = data.get("title")
    url = data.get("url")
    now = datetime.now()

    # Only store tab pings when Firefox is currently active. This avoids filling
    # the buffer with tabs from other browsers or when the user is inactive.
    is_firefox = False
    try:
        # Import window_tracker at call-time to allow tests or runtime patching of
        # get_active_target to take effect (avoids stale bindings from module import).
        import window_tracker
        aw = getattr(window_tracker, 'get_active_target', None)
        if callable(aw):
            aw = aw()
        aw_str = str(aw).lower() if aw is not None else ''
        is_firefox = ('firefox' in aw_str) or ('mozilla' in aw_str)
    except Exception:
        is_firefox = False

    if not is_firefox:
        return {"status": "ignored", "reason": "firefox_not_active"}

    # Store tabs keyed by URL and record the timestamp. This avoids creating a new
    # entry per incoming ping and lets the tracker deduplicate easily.
    active_tabs[url] = {"title": title, "url": url, "ts": now}

    return {"status": "ok"}

def run_listener():
    uvicorn.run(app, host="127.0.0.1", port=5000)

if __name__ == "__main__":
    run_listener()
