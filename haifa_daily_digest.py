#!/usr/bin/env python3
"""
🏗️ haifa_daily_digest.py
סקריפט יומי לסיכום אישורי בנייה ודיוני ועדה בחיפה
מקורות: מבא"ת (iplan) + complot חיפה
"""

import requests
import json
import os
import hashlib
import time
import smtplib
from datetime import datetime, timedelta
from pathlib import Path
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from bs4 import BeautifulSoup

# ─────────────────────────────────────────────
# ⚙️  הגדרות
# ─────────────────────────────────────────────
CONFIG = {
    "city_code": "6700",
    "city_name": "חיפה",
    "watch_streets": ["ויטקין", "אחוזה", "הרצל"],   # ← ערוך לפי רצונך

    "data_dir":    Path("./haifa_data"),
    "cache_file":  Path("./haifa_data/cache.json"),
    "report_html": Path("./haifa_data/daily_report.html"),
    "log_file":    Path("./haifa_data/digest.log"),

    "email": {
        "enabled":    True,
        "smtp_server": "smtp.gmail.com",
        "smtp_port":   587,
        # נקרא מ-GitHub Secrets (או מסביבה מקומית)
        "sender":    os.environ.get("EMAIL_SENDER", ""),
        "password":  os.environ.get("EMAIL_PASSWORD", ""),
        "recipient": os.environ.get("EMAIL_RECIPIENT", ""),
    }
}

# ─────────────────────────────────────────────
# 🔧  עזרים
# ─────────────────────────────────────────────
def log(msg):
    ts = datetime.now().strftime("%H:%M:%S")
    line = f"[{ts}] {msg}"
    print(line)
    CONFIG["log_file"].parent.mkdir(exist_ok=True)
    with open(CONFIG["log_file"], "a", encoding="utf-8") as f:
        f.write(line + "\n")

def load_cache() -> dict:
    if CONFIG["cache_file"].exists():
        with open(CONFIG["cache_file"], encoding="utf-8") as f:
            return json.load(f)
    return {}

def save_cache(cache: dict):
    CONFIG["cache_file"].parent.mkdir(exist_ok=True)
    with open(CONFIG["cache_file"], "w", encoding="utf-8") as f:
        json.dump(cache, f, ensure_ascii=False, indent=2)

# ─────────────────────────────────────────────
# 📡  מקור 1: מבא"ת – ArcGIS REST API
# ─────────────────────────────────────────────
IPLAN_BASE = "https://ags.iplan.gov.il/arcgisiplan/rest/services/PlanningPublic/Xplan/MapServer"

def fetch_mavat_plans(days_back=30) -> list:
    log("🔍 שולף נתונים ממבא\"ת...")
    cutoff = int((datetime.now() - timedelta(days=days_back)).timestamp() * 1000)
    url = f"{IPLAN_BASE}/1/query"
    params = {
        "where": f"CITY_CODE='{CONFIG['city_code']}' AND LAST_UPDATE_TIMESTAMP>={cutoff}",
        "outFields": "PLAN_NUMBER,PLAN_NAME,STATION_DESC,LAST_UPDATE,COMMITTEE_NAME",
        "returnGeometry": "false",
        "f": "json",
        "resultRecordCount": 200,
        "orderByFields": "LAST_UPDATE DESC",
    }
    try:
        r = requests.get(url, params=params, timeout=20)
        r.raise_for_status()
        features = r.json().get("features", [])
        log(f"  ✅ מבא\"ת: {len(features)} תכניות")
        return [f["attributes"] for f in features]
    except Exception as e:
        log(f"  ⚠️  שגיאת מבא\"ת: {e}")
        return []

def fetch_mavat_decisions(days_back=30) -> list:
    log("🔍 שולף החלטות ועדה...")
    cutoff = int((datetime.now() - timedelta(days=days_back)).timestamp() * 1000)
    url = f"{IPLAN_BASE}/4/query"
    params = {
        "where": f"CITY_CODE='{CONFIG['city_code']}' AND LAST_UPDATE_TIMESTAMP>={cutoff}",
        "outFields": "*",
        "returnGeometry": "false",
        "f": "json",
        "resultRecordCount": 100,
    }
    try:
        r = requests.get(url, params=params, timeout=20)
        r.raise_for_status()
        features = r.json().get("features", [])
        log(f"  ✅ החלטות ועדה: {len(features)} רשומות")
        return [f["attributes"] for f in features]
    except Exception as e:
        log(f"  ⚠️  שגיאת ועדה: {e}")
        return []

# ─────────────────────────────────────────────
# 📡  מקור 2: Complot חיפה
# ─────────────────────────────────────────────
def fetch_complot_permits(street: str = "") -> list:
    log(f"🔍 שולף מ-Complot {'רחוב ' + street if street else ''}...")
    headers = {
        "User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36",
        "Accept-Language": "he-IL,he;q=0.9",
    }
    results = []
    try:
        url = "https://haifa.complot.co.il/newengine/Pages/taba2.aspx"
        params = {"q": street} if street else {}
        r = requests.get(url, params=params, headers=headers, timeout=15)
        r.raise_for_status()
        soup = BeautifulSoup(r.text, "html.parser")
        for row in soup.select("tr"):
            cols = row.find_all("td")
            if len(cols) >= 3:
                results.append({
                    "permit_number": cols[0].get_text(strip=True),
                    "address":       cols[1].get_text(strip=True),
                    "status":        cols[2].get_text(strip=True),
                    "date":          cols[3].get_text(strip=True) if len(cols) > 3 else "",
                })
        log(f"  ✅ Complot: {len(results)} רשומות")
    except Exception as e:
        log(f"  ⚠️  Complot: {e}")
    return results

# ─────────────────────────────────────────────
# 🧠  ניתוח שינויים
# ─────────────────────────────────────────────
def detect_changes(plans: list, cache: dict) -> dict:
    prev_ids    = set(cache.get("plan_ids", []))
    current_ids = {str(p.get("PLAN_NUMBER", "")) for p in plans}
    new_ids     = current_ids - prev_ids
    return {
        "new_plans":  [p for p in plans if str(p.get("PLAN_NUMBER","")) in new_ids],
        "approved":   [p for p in plans if "בתוקף" in str(p.get("STATION_DESC","")) or "אושרה" in str(p.get("STATION_DESC",""))],
        "deposited":  [p for p in plans if "הפקדה" in str(p.get("STATION_DESC",""))],
        "total":      len(plans),
        "new_count":  len(new_ids),
    }

def filter_by_streets(plans, streets):
    if not streets:
        return plans
    return [p for p in plans if any(s in str(p.get("PLAN_NAME","")) for s in streets)]

# ─────────────────────────────────────────────
# 📄  דוח HTML
# ─────────────────────────────────────────────
def ts_to_date(ts) -> str:
    try:
        if ts:
            return datetime.fromtimestamp(int(ts) / 1000).strftime("%d/%m/%Y")
    except:
        pass
    return "—"

def plan_rows(items):
    if not items:
        return "<tr><td colspan='4' class='empty'>אין רשומות</td></tr>"
    rows = ""
    for p in items[:30]:
        num  = p.get("PLAN_NUMBER", "—")
        name = p.get("PLAN_NAME", "—")
        stat = p.get("STATION_DESC", "—")
        date = ts_to_date(p.get("LAST_UPDATE"))
        cls  = "approved" if "בתוקף" in stat or "אושרה" in stat else \
               "deposited" if "הפקדה" in stat else "other"
        link = f"https://mavat.iplan.gov.il/SV4/1/{num}"
        rows += f"<tr><td><a href='{link}' target='_blank' class='plan-link'>{num}</a></td><td>{name}</td><td><span class='badge {cls}'>{stat}</span></td><td>{date}</td></tr>"
    return rows

def decision_rows(items):
    if not items:
        return "<tr><td colspan='3' class='empty'>אין החלטות</td></tr>"
    rows = ""
    for d in items[:20]:
        name = d.get("PLAN_NAME") or d.get("OBJECT_NAME", "—")
        comm = d.get("COMMITTEE_NAME", "—")
        date = ts_to_date(d.get("LAST_UPDATE"))
        rows += f"<tr><td>{name}</td><td>{comm}</td><td>{date}</td></tr>"
    return rows

def complot_rows(items):
    if not items:
        return "<tr><td colspan='4' class='empty'>לא נמצאו נתונים (ייתכן חסימה זמנית)</td></tr>"
    rows = ""
    for c in items[:20]:
        rows += f"<tr><td>{c.get('permit_number','—')}</td><td>{c.get('address','—')}</td><td>{c.get('status','—')}</td><td>{c.get('date','—')}</td></tr>"
    return rows

def build_html_report(plans, decisions, complot, changes) -> str:
    today    = datetime.now().strftime("%d/%m/%Y %H:%M")
    approved = changes["approved"]
    deposited= changes["deposited"]
    new_plans= changes["new_plans"]

    watch_html = ""
    if CONFIG["watch_streets"]:
        watched = filter_by_streets(plans, CONFIG["watch_streets"])
        watch_html = f"""
        <section class="section">
          <h2>📍 רחובות במעקב – {', '.join(CONFIG['watch_streets'])}</h2>
          <table><thead><tr><th>מספר</th><th>שם תכנית</th><th>סטטוס</th><th>עדכון</th></tr></thead>
          <tbody>{plan_rows(watched)}</tbody></table>
        </section>"""

    new_section = ""
    if new_plans:
        new_section = f"""
        <section class="section highlight">
          <h2>🆕 תכניות חדשות מאז אתמול</h2>
          <table><thead><tr><th>מספר</th><th>שם תכנית</th><th>סטטוס</th><th>עדכון</th></tr></thead>
          <tbody>{plan_rows(new_plans)}</tbody></table>
        </section>"""

    return f"""<!DOCTYPE html>
<html lang="he" dir="rtl">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>דוח יומי – ועדה מקומית חיפה {today}</title>
<style>
  @import url('https://fonts.googleapis.com/css2?family=Heebo:wght@300;400;600;800&display=swap');
  :root {{
    --bg:#0e1117; --surface:#161b27; --border:#252d3d;
    --accent:#3b82f6; --green:#22c55e; --yellow:#eab308; --red:#ef4444;
    --text:#e2e8f0; --muted:#64748b;
  }}
  *{{box-sizing:border-box;margin:0;padding:0}}
  body{{font-family:'Heebo',sans-serif;background:var(--bg);color:var(--text);padding:24px 16px}}
  .header{{text-align:center;margin-bottom:32px}}
  .header h1{{font-size:1.9rem;font-weight:800;color:#fff}}
  .header p{{color:var(--muted);font-size:.9rem;margin-top:6px}}
  .stats{{display:flex;gap:14px;flex-wrap:wrap;justify-content:center;margin-bottom:32px}}
  .stat-card{{background:var(--surface);border:1px solid var(--border);border-radius:12px;
    padding:18px 24px;text-align:center;flex:1;min-width:120px}}
  .stat-card .num{{font-size:2rem;font-weight:800}}
  .stat-card .lbl{{font-size:.76rem;color:var(--muted);margin-top:4px}}
  .blue{{color:var(--accent)}} .green{{color:var(--green)}} .yellow{{color:var(--yellow)}}
  .section{{background:var(--surface);border:1px solid var(--border);border-radius:12px;
    padding:22px;margin-bottom:20px}}
  .section.highlight{{border-color:var(--accent)}}
  .section h2{{font-size:1rem;font-weight:700;margin-bottom:14px;
    padding-bottom:10px;border-bottom:1px solid var(--border)}}
  table{{width:100%;border-collapse:collapse;font-size:.85rem}}
  th{{color:var(--muted);font-weight:600;text-align:right;padding:7px 10px;
    border-bottom:1px solid var(--border)}}
  td{{padding:8px 10px;border-bottom:1px solid #1a2030;vertical-align:middle}}
  tr:last-child td{{border-bottom:none}}
  .badge{{display:inline-block;padding:2px 10px;border-radius:999px;font-size:.76rem;font-weight:600}}
  .badge.approved{{background:rgba(34,197,94,.15);color:var(--green)}}
  .badge.deposited{{background:rgba(234,179,8,.15);color:var(--yellow)}}
  .badge.other{{background:rgba(100,116,139,.2);color:var(--muted)}}
  .plan-link{{color:var(--accent);text-decoration:none}}
  .empty{{color:var(--muted);font-style:italic;padding:18px;text-align:center}}
  .footer{{text-align:center;color:var(--muted);font-size:.76rem;margin-top:28px}}
  .footer a{{color:var(--accent)}}
</style>
</head>
<body>
<div class="header">
  <h1>🏗️ דוח ועדה מקומית – חיפה</h1>
  <p>עודכן: {today} | אוטומטי דרך GitHub Actions</p>
</div>

<div class="stats">
  <div class="stat-card"><div class="num blue">{changes['total']}</div><div class="lbl">תכניות פעילות</div></div>
  <div class="stat-card"><div class="num green">{len(approved)}</div><div class="lbl">מאושרות</div></div>
  <div class="stat-card"><div class="num yellow">{len(deposited)}</div><div class="lbl">בהפקדה</div></div>
  <div class="stat-card"><div class="num blue">{changes['new_count']}</div><div class="lbl">חדשות היום</div></div>
  <div class="stat-card"><div class="num blue">{len(decisions)}</div><div class="lbl">דיוני ועדה</div></div>
</div>

{new_section}
{watch_html}

<section class="section">
  <h2>✅ תכניות שאושרו (30 יום אחרונים)</h2>
  <table><thead><tr><th>מספר</th><th>שם תכנית</th><th>סטטוס</th><th>תאריך</th></tr></thead>
  <tbody>{plan_rows(approved)}</tbody></table>
</section>

<section class="section">
  <h2>📋 בהפקדה – ניתן להגיש התנגדויות</h2>
  <table><thead><tr><th>מספר</th><th>שם תכנית</th><th>סטטוס</th><th>תאריך</th></tr></thead>
  <tbody>{plan_rows(deposited)}</tbody></table>
</section>

<section class="section">
  <h2>🗓️ דיוני ועדה (30 יום אחרונים)</h2>
  <table><thead><tr><th>נושא/תכנית</th><th>ועדה</th><th>תאריך</th></tr></thead>
  <tbody>{decision_rows(decisions)}</tbody></table>
</section>

<section class="section">
  <h2>📄 היתרי בנייה – Complot חיפה</h2>
  <table><thead><tr><th>מספר היתר</th><th>כתובת</th><th>סטטוס</th><th>תאריך</th></tr></thead>
  <tbody>{complot_rows(complot)}</tbody></table>
</section>

<div class="footer">
  <p>
    <a href="https://mavat.iplan.gov.il">מבא"ת</a> ·
    <a href="https://haifa.complot.co.il">Complot חיפה</a> ·
    <a href="https://www.haifa.muni.il">עיריית חיפה</a>
  </p>
</div>
</body></html>"""

# ─────────────────────────────────────────────
# 📧  שליחת מייל
# ─────────────────────────────────────────────
def send_email(subject: str, html_body: str):
    cfg = CONFIG["email"]
    if not cfg["enabled"] or not cfg["sender"]:
        log("⚠️  מייל לא מוגדר – מדלג")
        return
    try:
        msg = MIMEMultipart("alternative")
        msg["Subject"] = subject
        msg["From"]    = cfg["sender"]
        msg["To"]      = cfg["recipient"]
        msg.attach(MIMEText(html_body, "html", "utf-8"))
        with smtplib.SMTP(cfg["smtp_server"], cfg["smtp_port"]) as s:
            s.starttls()
            s.login(cfg["sender"], cfg["password"])
            s.sendmail(cfg["sender"], cfg["recipient"], msg.as_string())
        log("📧 מייל נשלח בהצלחה!")
    except Exception as e:
        log(f"⚠️  שגיאת מייל: {e}")

# ─────────────────────────────────────────────
# 🚀  ריצה ראשית
# ─────────────────────────────────────────────
def main():
    CONFIG["data_dir"].mkdir(exist_ok=True)
    log("=" * 50)
    log(f"🏗️  דוח יומי – ועדה מקומית חיפה")
    log(f"📅  {datetime.now().strftime('%d/%m/%Y %H:%M')}")
    log("=" * 50)

    cache     = load_cache()
    plans     = fetch_mavat_plans(days_back=30)
    decisions = fetch_mavat_decisions(days_back=30)

    complot_results = []
    for street in (CONFIG["watch_streets"] or [""]):
        complot_results.extend(fetch_complot_permits(street))
        time.sleep(1)

    changes = detect_changes(plans, cache)
    log(f"📊 חדשות: {changes['new_count']} | מאושרות: {len(changes['approved'])} | בהפקדה: {len(changes['deposited'])}")

    html = build_html_report(plans, decisions, complot_results, changes)
    CONFIG["report_html"].write_text(html, encoding="utf-8")
    log(f"✅ דוח נשמר: {CONFIG['report_html']}")

    cache["plan_ids"]   = [str(p.get("PLAN_NUMBER","")) for p in plans]
    cache["last_run"]   = datetime.now().isoformat()
    save_cache(cache)

    subj = f"🏗️ דוח ועדה חיפה {datetime.now().strftime('%d/%m/%Y')} – {changes['new_count']} חדשות, {len(changes['approved'])} מאושרות"
    send_email(subj, html)
    log("🎉 סיום!")

if __name__ == "__main__":
    main()
