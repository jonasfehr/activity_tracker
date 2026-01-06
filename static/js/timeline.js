document.addEventListener('DOMContentLoaded', () => {
  try {
    const events = window.EVENTS || [];
    const day = window.DAY;
    let focusMode = !!window.FOCUS;
    const timeline = document.getElementById('timeline');
    const labels = document.getElementById('timeLabels');
    const eventsCountEl = document.getElementById('eventsCount');
    const focusToggle = document.getElementById('focusToggle');
    const heightRange = document.getElementById('heightRange');
    const toggleDay = document.getElementById('toggleDay');
    const todayBtn = document.getElementById('todayBtn');
    const noticeArea = document.getElementById('noticeArea');

    document.documentElement.style.setProperty('--timeline-height', (window.HEIGHT||1200) + 'px');


    function showNotice(msg, success=true, timeout=3000) {
      if (!noticeArea) return;
      const d = document.createElement('div');
      d.className = 'notice-banner' + (success ? ' success' : ' error');
      d.innerText = msg;
      noticeArea.innerHTML = '';
      noticeArea.appendChild(d);
      setTimeout(()=>{ if (noticeArea.contains(d)) noticeArea.removeChild(d); }, timeout);
    }

    function timeToMs(t) { const v = new Date(t).getTime(); return isNaN(v) ? null : v; }

    function cssColorFor(str) {
      try {
        let h = 0;
        for (let i=0;i<str.length;i++) h = (h*31 + str.charCodeAt(i)) % 360;
        return 'hsl(' + h + ',70%,40%)';
      } catch (e) {
        return '#444';
      }
    }

    function normalizeTitle(raw) {
      if (!raw) return '';
      const lower = String(raw).toLowerCase();
      // If it mentions firefox anywhere, normalize to 'Firefox'
      if (lower.includes('firefox') || lower.includes('mozilla')) return 'Firefox';

      // Tabs from our extension often are "page title - url"; detect URL and treat as Firefox
      if (typeof raw === 'string' && (raw.includes('http://') || raw.includes('https://') || raw.includes('://'))) {
        return 'Firefox';
      }

      // Prefer the left side of separators as the program/source name
      const emIndex = raw.indexOf('—');
      if (emIndex !== -1) return raw.slice(0, emIndex).trim();
      const dashIndex = raw.indexOf(' - ');
      if (dashIndex !== -1) return raw.slice(0, dashIndex).trim();

      // fallback: return whole string
      return raw;
    }

    function render() {
      const fullStart = new Date(day + 'T00:00:00').getTime();
      const fullEnd = new Date(day + 'T23:59:59').getTime();

      // Determine the visible window: if focusMode and there are events, reduce to min/max timestamps
      let winStart = fullStart;
      let winEnd = fullEnd;

      // compute numeric starts/ends for events
      const evBounds = events
        .map(ev => {
          let s = ev.start; let e = ev.end;
          if (typeof s === 'number' && s < 1e12) s = s * 1000;
          if (typeof e === 'number' && e < 1e12) e = e * 1000;
          s = timeToMs(s); e = timeToMs(e);
          return (isFinite(s) && isFinite(e)) ? {s,e} : null;
        })
        .filter(Boolean);

      if (focusMode && evBounds.length > 0) {
        let minS = Math.min(...evBounds.map(x => x.s));
        let maxE = Math.max(...evBounds.map(x => x.e));
        // add a small padding (5 minutes)
        const pad = 5 * 60 * 1000;
        winStart = Math.max(fullStart, minS - pad);
        winEnd = Math.min(fullEnd, maxE + pad);
        // ensure minimal visible span (15 minutes)
        if (winEnd - winStart < 15 * 60 * 1000) {
          const mid = Math.round((winStart + winEnd)/2);
          winStart = mid - 7.5 * 60 * 1000;
          winEnd = mid + 7.5 * 60 * 1000;
        }
      } else if (focusMode) {
        // no events, fall back to default 08:00-20:00 when focusing
        winStart = new Date(day + 'T08:00:00').getTime();
        winEnd = new Date(day + 'T20:00:00').getTime();
      }

      const winSpan = winEnd - winStart;

      // scale the container height based on winSpan and user-selected base height
      const baseHeight = parseInt(heightRange.value || window.HEIGHT || 1200, 10) || 1200;
      // use 12 hours as a baseline (so default focus 08:00-20:00 equals baseHeight)
      const twelveH = 12 * 60 * 60 * 1000;
      let computedHeight = Math.round((winSpan / twelveH) * baseHeight);
      // allow filling the viewport when in focus mode so the timeline can still take full screen
      try { if (focusMode) computedHeight = Math.max(computedHeight, Math.round(window.innerHeight * 0.85)); } catch(e) {}
      computedHeight = Math.max(300, Math.min(3000, computedHeight));
      document.documentElement.style.setProperty('--timeline-height', computedHeight + 'px');

      // debug info in console
      try { console.debug('Timeline render:', {day, focusMode, eventsCount: events.length, winStart: new Date(winStart).toISOString(), winEnd: new Date(winEnd).toISOString(), height: computedHeight}) } catch(e) {}

      // draw time labels: choose hour marks covering winStart..winEnd
      labels.innerHTML = '';
      const h0 = new Date(winStart);
      h0.setMinutes(0,0,0);
      if (h0.getTime() > winStart) h0.setHours(h0.getHours() - 1);
      for (let t = h0.getTime(); t <= winEnd + 1; t += 60 * 60 * 1000) {
        if (t < winStart) continue;
        const pct = (t - winStart) / winSpan * 100;
        const div = document.createElement('div');
        div.className = 'time-label';
        div.style.top = pct + '%';
        const hh = new Date(t).getHours().toString().padStart(2,'0');
        div.innerText = hh + ':00';
        labels.appendChild(div);
      }

      // grid (hour + quarter-hour lines)
      const grid = document.createElement('div');
      grid.className = 'grid';
      const fifteen = 15 * 60 * 1000;
      const firstMark = Math.floor(winStart / fifteen) * fifteen;
      for (let t = firstMark; t <= winEnd + 1; t += fifteen) {
        if (t < winStart) continue;
        const pct = (t - winStart) / winSpan * 100;
        const line = document.createElement('div');
        const dt = new Date(t);
        if (dt.getMinutes() === 0) {
          line.className = 'grid-line hour';
        } else {
          line.className = 'grid-line quarter';
        }
        line.style.top = pct + '%';
        grid.appendChild(line);
      }

      // clear timeline and append grid + events layer
      timeline.innerHTML = '';
      // append grid (recreate content)
      timeline.appendChild(grid);

      // ensure grid is visible above events (overlay) so thin lines are always visible
      grid.style.zIndex = '3';
      grid.style.display = 'block';
      grid.style.width = '100%';

      // create or reuse events layer (ensure it's always defined)
      let eventsLayer = timeline.querySelector('.events-layer');
      if (!eventsLayer) {
        eventsLayer = document.createElement('div');
        eventsLayer.className = 'events-layer';
        timeline.appendChild(eventsLayer);
      } else {
        eventsLayer.innerHTML = '';
      }

      eventsLayer.style.position = 'absolute';
      eventsLayer.style.left = '0';
      eventsLayer.style.right = '0';
      eventsLayer.style.top = '0';
      eventsLayer.style.bottom = '0';
      eventsLayer.style.zIndex = '2';

      // render events with clamping and robustness
      const seen = {}; // map displayName -> color to ensure same color per program

      // track how many DOM events are appended
      let appended = 0;
      events.forEach(ev => {
        let s_raw = ev.start;
        let e_raw = ev.end;
        if (typeof s_raw === 'number' && s_raw < 1e12) s_raw = s_raw * 1000;
        if (typeof e_raw === 'number' && e_raw < 1e12) e_raw = e_raw * 1000;

        const s = timeToMs(s_raw);
        const e = timeToMs(e_raw);
        if (!s || !e || !isFinite(s) || !isFinite(e)) return;

        const start = Math.max(s, winStart);
        const end = Math.min(e, winEnd);
        // Allow zero-length events (end === start) to render as a tiny visible block
        // (used for browser-tab events). Only skip when end < start due to clipping.
        if (end < start) return;

        let topPct = (start - winStart) / winSpan * 100;
        let heightPct = (end - start) / winSpan * 100;
        if (!isFinite(topPct) || isNaN(topPct)) return;
        topPct = Math.max(0, Math.min(100, topPct));
        heightPct = Math.max(0.5, Math.min(100 - topPct, heightPct));

        // normalize display name and pick a consistent color
        const displayName = normalizeTitle(ev.title);
        if (!seen[displayName]) seen[displayName] = cssColorFor(displayName);
        const color = seen[displayName];

        const el = document.createElement('div');
        el.className = 'event';
        el.style.top = topPct + '%';
        el.style.height = heightPct + '%';
        el.style.background = color;
        // show only the full title text (no duplicated meta line)
        const titleSpan = document.createElement('span');
        titleSpan.className = 'title';
        titleSpan.textContent = ev.title || displayName;
        el.appendChild(titleSpan);
        // accessibility
        el.setAttribute('aria-label', ev.title || displayName);
        el.setAttribute('role', 'listitem');
        el.setAttribute('tabindex', '0');
        el.title = (ev.title || displayName) + '\n' + new Date(s).toLocaleString() + ' - ' + new Date(e).toLocaleString();
        // keyboard: Enter/Space opens tooltip-like alert (simple accessible fallback)
        el.addEventListener('keydown', (evk)=>{ if (evk.key === 'Enter' || evk.key === ' ') { evk.preventDefault(); alert(el.title); } });
        eventsLayer.appendChild(el);
        appended += 1;
      });

      if (appended === 0) {
        const note = document.createElement('div');
        note.className = 'empty-state';
        note.innerText = 'Keine sichtbaren Einträge im aktuellen Fokus.';
        timeline.appendChild(note);
      }

      // update events counter UI
      if (eventsCountEl) {
        eventsCountEl.innerText = appended + ' Einträge';
      }

      // debug: counts
      try { console.debug('grid-lines=', grid.querySelectorAll('.grid-line').length, 'events=', events.length, 'appended=', appended); } catch(e) {}

      // no legend anymore - titles are shown inside blocks
    }

    // wire up controls
    if (focusToggle) focusToggle.addEventListener('change', e => { focusMode = e.target.checked; render(); });
    if (toggleDay) toggleDay.addEventListener('click', () => { focusMode = !focusMode; if (focusToggle) focusToggle.checked = focusMode; render(); });
    if (heightRange) heightRange.addEventListener('input', e => { document.documentElement.style.setProperty('--timeline-height', e.target.value + 'px'); render(); });
    if (todayBtn) todayBtn.addEventListener('click', () => { window.location.href = '/timeline?day=' + new Date().toISOString().slice(0,10); });



    // initial
    render();
  } catch (err) {
    console.error('Timeline init error', err);
    const t = document.getElementById('timeline');
    if (t) {
      const errDiv = document.createElement('div');
      errDiv.className = 'error-banner';
      errDiv.innerText = 'Timeline Fehler: ' + (err && err.message ? err.message : String(err));
      t.innerHTML = '';
      t.appendChild(errDiv);
    }
  }
});