from ics import Calendar, Event
from database import get_blocks_for_day
from datetime import date

def export_ical():
    cal = Calendar()
    today = date.today().isoformat()

    for _, start, end, title in get_blocks_for_day(today):
        e = Event()
        e.name = title
        e.begin = start
        e.end = end
        cal.events.add(e)

    with open(f"activity-{today}.ics", "w") as f:
        f.writelines(cal)

def export_csv():
    today = date.today().isoformat()
    rows = get_blocks_for_day(today)

    with open(f"activity-{today}.csv", "w") as f:
        f.write("start,end,title\n")
        for _, start, end, title in rows:
            f.write(f"{start},{end},{title}\n")