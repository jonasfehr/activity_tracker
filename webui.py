from fastapi import FastAPI, Query, Request
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.responses import HTMLResponse
from exporter import export_ical, export_csv
from database import get_blocks_for_day
from datetime import date, datetime
import json
import logging

logger = logging.getLogger(__name__)
if not logging.getLogger().handlers:
    logging.basicConfig(level=logging.INFO)

app = FastAPI()
# serve static files and templates
app.mount('/static', StaticFiles(directory='static'), name='static')
templates = Jinja2Templates(directory='templates')

@app.get("/", response_class=HTMLResponse)
def ui():
    today = date.today().isoformat()
    blocks = get_blocks_for_day(today)

    rows = "".join(
        f"<div>{b[1]} – {b[2]} : {b[3]}</div>"
        for b in blocks
    )

    return f"""
    <h2>Aktivität {today}</h2>
    {rows}
    <br>
    <a href="/timeline">Timeline</a><br>
    <a href="/export/ical">Export iCal</a><br>
    <a href="/export/csv">Export CSV</a>
    """

@app.get("/export/ical")
def do_ical():
    export_ical()
    return {"status": "ok"}

@app.get("/export/csv")
def do_csv():
    export_csv()
    return {"status": "ok"}


@app.get("/timeline", response_class=HTMLResponse)
def timeline(request: Request, day: str = None, focus: int = Query(1), height: int = Query(1200)):
    """Show a vertical day timeline.

    Query params:
    - day: YYYY-MM-DD (default: today)
    - focus: 1 => focus on 08:00-20:00, 0 => show full day
    - height: pixel height for timeline container (adjustable)
    """
    day_str = day or date.today().isoformat()
    try:
        rows = get_blocks_for_day(day_str)

        # Convert to epoch milliseconds on the server to avoid client-side
        # parsing/timezone inconsistencies. This makes top/height calculations
        # precise and consistent across browsers.
        events = []
        for r in rows:
            # r[1] and r[2] are ISO timestamp strings from the DB. Convert to epoch ms.
            try:
                s_dt = datetime.fromisoformat(r[1])
                e_dt = datetime.fromisoformat(r[2])
                events.append({
                    "start": int(s_dt.timestamp() * 1000),
                    "end": int(e_dt.timestamp() * 1000),
                    "title": r[3],
                })
            except Exception:
                # Fallback: if not ISO, try parsing with datetime.fromisoformat after trimming
                try:
                    s_dt = datetime.fromisoformat(str(r[1]).strip())
                    e_dt = datetime.fromisoformat(str(r[2]).strip())
                    events.append({"start": int(s_dt.timestamp() * 1000), "end": int(e_dt.timestamp() * 1000), "title": r[3]})
                except Exception:
                    # final fallback: pass raw strings (client will handle them)
                    events.append({"start": r[1], "end": r[2], "title": r[3]})

        events_json = json.dumps(events)
        logger.info("Serving timeline for %s with %d events", day_str, len(events))
        return templates.TemplateResponse("timeline.html", {"request": request, "events_json": events_json, "day": day_str, "focus": bool(focus), "height": int(height)})
    except Exception as e:
        logger.exception("Error rendering timeline for %s", day_str)
        # return a minimal safe page instead of allowing a crash
        return HTMLResponse(content=f"<html><body><h2>Fehler beim Laden der Timeline</h2><pre>{str(e)}</pre></body></html>", status_code=500)


@app.post("/admin/trim_until")
def admin_trim_until(substring: str = "firefox", day: str = None):
    """Delete all blocks for the given day that occur before the first block
    whose title contains `substring` (case-insensitive). Defaults to today and
    'firefox'. Returns the number of deleted rows."""
    day_str = day or date.today().isoformat()
    from database import delete_until_first_title_contains
    deleted = delete_until_first_title_contains(day_str, substring)
    return {"deleted": deleted}


@app.get('/health')
def health():
    """Simple health-check endpoint for monitoring (returns 200 OK)."""
    return {"status": "ok"}


@app.get('/admin/events')
def admin_events(day: str = None):
    """Return processed events as JSON (epoch ms) for the given day. Useful for curl-based debugging."""
    day_str = day or date.today().isoformat()
    try:
        rows = get_blocks_for_day(day_str)
        events = []
        for r in rows:
            try:
                s_dt = datetime.fromisoformat(r[1])
                e_dt = datetime.fromisoformat(r[2])
                events.append({
                    'start': int(s_dt.timestamp() * 1000),
                    'end': int(e_dt.timestamp() * 1000),
                    'title': r[3],
                })
            except Exception:
                try:
                    s_dt = datetime.fromisoformat(str(r[1]).strip())
                    e_dt = datetime.fromisoformat(str(r[2]).strip())
                    events.append({'start': int(s_dt.timestamp() * 1000), 'end': int(e_dt.timestamp() * 1000), 'title': r[3]})
                except Exception:
                    events.append({'start': r[1], 'end': r[2], 'title': r[3]})
        return {'day': day_str, 'events': events}
    except Exception as e:
        logger.exception('admin_events failed for %s', day_str)
        return {'error': str(e)}


@app.get('/admin/positions')
def admin_positions(day: str = None, focus: int = Query(1)):
    """Return computed top/height (percent) per event for debugging in curl tests."""
    day_str = day or date.today().isoformat()
    try:
        resp = admin_events(day=day_str)
        if 'events' not in resp:
            return {'error': 'no events', 'raw': resp}
        events = resp['events']
        # compute numeric bounds
        nums = []
        for ev in events:
            s = ev['start'] if isinstance(ev['start'], int) else None
            e = ev['end'] if isinstance(ev['end'], int) else None
            if s is None or e is None:
                try:
                    s = int(datetime.fromisoformat(str(ev['start'])).timestamp() * 1000)
                    e = int(datetime.fromisoformat(str(ev['end'])).timestamp() * 1000)
                except Exception:
                    s = None; e = None
            if s and e:
                nums.append((s,e,ev['title']))
        if focus and nums:
            minS = min(s for s,e,_ in nums)
            maxE = max(e for _,e,_ in nums)
            pad = 5 * 60 * 1000
            winStart = max(int(datetime.fromisoformat(day_str + 'T00:00:00').timestamp() * 1000), minS - pad)
            winEnd = min(int(datetime.fromisoformat(day_str + 'T23:59:59').timestamp() * 1000), maxE + pad)
        elif focus:
            winStart = int(datetime.fromisoformat(day_str + 'T08:00:00').timestamp() * 1000)
            winEnd = int(datetime.fromisoformat(day_str + 'T20:00:00').timestamp() * 1000)
        else:
            winStart = int(datetime.fromisoformat(day_str + 'T00:00:00').timestamp() * 1000)
            winEnd = int(datetime.fromisoformat(day_str + 'T23:59:59').timestamp() * 1000)
        winSpan = winEnd - winStart
        out = []
        for s,e,title in nums:
            if e <= winStart or s >= winEnd:
                continue
            start = max(s, winStart)
            end = min(e, winEnd)
            topPct = (start - winStart) / winSpan * 100
            heightPct = (end - start) / winSpan * 100
            out.append({'title': title, 'start': start, 'end': end, 'topPct': topPct, 'heightPct': heightPct})
        return {'day': day_str, 'winStart': winStart, 'winEnd': winEnd, 'positions': out}
    except Exception as e:
        logger.exception('admin_positions failed for %s', day_str)
        return {'error': str(e)}

