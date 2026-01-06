# Activity Tracker

Kurze Übersicht

Ein kleines lokales Tool, das aktive Fenster- und Browser-Tab-Aktivitäten aufzeichnet und als Tages-Timeline darstellt. Es besteht aus mehreren Komponenten:

- `tabListener.py` – eine FastAPI-App, die Tab-Pings (von der Firefox-Erweiterung) empfängt.
- `tracker.py` – verarbeitet periodisch aktive Fenster / gesammelte Tabs und schreibt Blöcke in die SQLite-Datenbank.
- `webui.py` – FastAPI-Web UI, zeigt die aktuelle Aktivität und eine visuelle Timeline für Tage an.
- `database.py` – einfache SQLite-Werkzeuge zum Speichern/Lesen von Blöcken.
- `friefoxPlugin/` – Beispiel-Firefox-Extension, die aktive Tabs per HTTP an `tabListener` sendet.

---

## Voraussetzungen

- Python 3.9 oder neuer (das Projekt wurde mit Python 3.9 getestet)
- Empfohlen: `pyenv` + virtuelle Umgebung
- Browser (Firefox) für die Tab-Integration

Installiere die Python-Abhängigkeiten:

```bash
python -m pip install -r requirements.txt
```

---

## Schnellstart (lokal)

Das Repository enthält eine bequeme "all-in-one" Startdatei `main.py`, die die Tab-Listener-App, den Tracker-Loop und die Web‑UI startet:

```bash
python main.py
```

- Die Web-UI ist danach erreichbar unter: `http://127.0.0.1:9432/`
- Der Tab‑Listener läuft auf `http://127.0.0.1:5000/tab` und erwartet POSTs mit JSON `{"title":"...","url":"..."}` (die Extension schickt das automatisch alle 10s).

Hinweis: Alternativ kannst du die Komponenten separat starten:

- Tab listener: `python tabListener.py` (startet eine FastAPI/uvicorn Instanz auf Port 5000)
- Tracker Loop: `python tracker.py` oder `python -c "from tracker import run_periodic; run_periodic()"` (läuft im Blocking Loop)
- Web UI: mit uvicorn: `uvicorn webui:app --reload --port 9432`

---

## Konfiguration

Die wichtigsten Einstellungen findest du in `config.py`:

- `TRACK_INTERVAL_SECONDS` – Polling-Intervall des Trackers (Standard: 5s)
- `BUCKET_MINUTES` – Größe eines Buckets in Minuten (Standard: 5)
- `MERGE_GAP_SECONDS` – Schwellwert in Sekunden, bei dem zwei zeitlich nahe Blöcke mit gleichem Titel zusammengeführt werden (Standard: 5)
- `DB_PATH` – Pfad zur SQLite-Datenbank (Standard: `activity.db`)

Für Tests wird `DB_PATH` in den Testfällen temporär überschrieben, sodass lokale DB-Dateien nicht beeinflusst werden.

---

## Firefox Erweiterung (Development)

Im Verzeichnis `friefoxPlugin/` findest du eine einfache Beispiel-Extension, die alle 10s das aktuelle Tab an `http://127.0.0.1:5000/tab` sendet. Zum Laden in Firefox (temporär):

1. Öffne `about:debugging#/runtime/this-firefox`
2. Wähle "Load Temporary Add-on" und lade `friefoxPlugin/manifest.json`

Die Extension sendet `title` und `url` des aktiven Tabs als JSON POST.

---

## Datenbank & Verhalten

- Ereignisse werden als Blöcke (`start`, `end`, `title`) in SQLite gespeichert.
- `insert_block` fügt neue Blöcke hinzu oder merged vorhandene Blöcke mit gleichem Titel, wenn sie weniger als `MERGE_GAP_SECONDS` auseinanderliegen.
- Tab-Ereignisse werden als sehr kurze Blöcke (Start == End) gespeichert; die Web-Timeline rendert diese als kleine sichtbare Einträge.
- Um Flooding durch die Extension zu vermeiden:
  - `tabListener` speichert Tabs **nur**, wenn Firefox tatsächlich aktiv ist.
  - Tabs werden nach URL dedupliziert (nur der letzte Ping pro URL bleibt im Puffer).
  - `tracker` verarbeitet den Puffer einmal pro Zyklus und leert ihn anschließend.

---

## Tests

Tests befinden sich im Verzeichnis `tests/` und verwenden `unittest`.

- Unit-Tests ausführen:

```bash
python -m pytest -q
```

Wichtige Testfälle:

- `tests/test_database.py` – Tests für Merge-/Insert-Verhalten und Tab-Inserts
- `tests/test_tracker.py` – Tests für deduplizierende Tab-Verarbeitung und API-Verhalten

Wenn du ein neues Feature hinzufügst, bitte Tests ergänzen, damit Regressionen verhindert werden.

---

## Entwicklungstipps

- Verwende temporäre DBs in Tests (siehe bereits vorhandene Tests), damit deine lokale `activity.db` nicht verändert wird.
- Beim Debugging der Timeline helfen die Admin-Endpunkte:
  - `/admin/events?day=YYYY-MM-DD` – gibt die verarbeiteten Events als JSON zurück (epoch ms)
  - `/admin/positions?day=YYYY-MM-DD` – gibt die berechneten top/height Positionen (percent) zurück

- Um Änderungen an der Frontend-Logik zu prüfen, öffne die Entwicklerkonsole des Browsers; die Timeline-Skripte schreiben Debug‑Infos (console.debug).

---

## Contribution & License

Wenn du Änderungen beitragen möchtest:

1. Forke das Repo
2. Erstelle einen Branch für dein Feature/Hotfix
3. Füge Tests hinzu oder erweitere vorhandene
4. Öffne einen Pull Request mit einer kurzen Beschreibung

Lizenz: Füge hier deine Lizenzangabe ein (z. B. MIT) oder ergänze `LICENSE`.

---

## FAQs / Troubleshooting

- "Timeline zeigt 0 Einträge, obwohl die Startseite Einträge hat"
  - Stelle sicher, dass die Seite neu geladen wurde und kein JS-Fehler (öffne DevTools -> Console).
  - Prüfe `/admin/events?day=YYYY-MM-DD` ob Events serverseitig vorhanden sind.
  - Eventuell wurden punktuelle Tab-Events zuvor ausgefiltert – die aktuelle Version rendert auch Start==End Einträge.

- "DB wird mit vielen Einträgen zugemüllt"
  - Stelle sicher, dass die Firefox-Extension nur läuft, wenn Firefox aktiv ist (das Backend ignoriert Pings falls nicht).

---

Wenn du möchtest, schreibe ich dir noch eine kurze `CONTRIBUTING.md`-Datei oder ergänze CI-Schritte (Github Actions) für `pytest`. Viel Erfolg beim Testen und Entwickeln!
