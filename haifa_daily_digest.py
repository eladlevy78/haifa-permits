#!/usr/bin/env python3
"""
haifa_daily_digest.py v3
׳“׳•׳— ׳™׳•׳׳™ ג€“ ׳•׳¢׳“׳” ׳׳§׳•׳׳™׳× ׳—׳™׳₪׳”
׳׳•׳’׳™׳§׳” ׳׳‘׳•׳¡׳¡׳× ׳’׳™׳׳•׳™ ׳׳׳™׳×׳™ ׳©׳ ׳׳‘׳ ׳” ׳”׳׳×׳¨
"""

import requests, json, os, time, smtplib, re, base64
from datetime import datetime, timedelta
from pathlib import Path
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from bs4 import BeautifulSoup

# ג”€ג”€ ׳”׳’׳“׳¨׳•׳× ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€
CONFIG = {
    "data_dir":    Path("./haifa_data"),
    "cache_file":  Path("./haifa_data/cache.json"),
    "report_html": Path("./haifa_data/daily_report.html"),
    "log_file":    Path("./haifa_data/digest.log"),
    "days_back":   30,
    "email": {
        "enabled":    True,
        "smtp_server": "smtp.gmail.com",
        "smtp_port":   587,
        "sender":    os.environ.get("EMAIL_SENDER", ""),
        "password":  os.environ.get("EMAIL_PASSWORD", ""),
        "recipient": os.environ.get("EMAIL_RECIPIENT", ""),
    }
}

COMPLOT_BASE = "https://haifa.complot.co.il"
ARCHIVE_BASE = "https://archive.gis-net.co.il"
SITE_ID      = "16"

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/124.0 Safari/537.36",
    "Accept-Language": "he-IL,he;q=0.9",
    "Referer": COMPLOT_BASE + "/",
}

# ג”€ג”€ ׳¢׳–׳¨׳™׳ ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€
def log(msg):
    ts = datetime.now().strftime("%H:%M:%S")
    print(f"[{ts}] {msg}")
    CONFIG["log_file"].parent.mkdir(exist_ok=True)
    with open(CONFIG["log_file"], "a", encoding="utf-8") as f:
        f.write(f"[{ts}] {msg}\n")

def load_cache():
    if CONFIG["cache_file"].exists():
        with open(CONFIG["cache_file"], encoding="utf-8") as f:
            return json.load(f)
    return {}

def save_cache(c):
    CONFIG["cache_file"].parent.mkdir(exist_ok=True)
    with open(CONFIG["cache_file"], "w", encoding="utf-8") as f:
        json.dump(c, f, ensure_ascii=False, indent=2)

# ג”€ג”€ ׳©׳׳™׳₪׳× ׳¨׳©׳™׳׳× ׳™׳©׳™׳‘׳•׳× ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€
def fetch_meetings(days_back=30):
    """׳©׳•׳׳£ ׳¨׳©׳™׳׳× ׳™׳©׳™׳‘׳•׳× ׳-Complot API"""
    log("Complot ג€“ ׳©׳•׳׳£ ׳¨׳©׳™׳׳× ׳™׳©׳™׳‘׳•׳×...")
    today = datetime.now()
    fd = (today - timedelta(days=days_back)).strftime("%d/%m/%Y")
    td = today.strftime("%d/%m/%Y")

    session = requests.Session()
    session.headers.update(HEADERS)

    # ׳˜׳¢׳ ׳“׳£ ׳¨׳׳©׳™ ׳׳§׳‘׳׳× cookies
    try:
        session.get(COMPLOT_BASE + "/yeshivot/", timeout=10)
        time.sleep(1)
    except:
        pass

    # ׳©׳׳•׳£ ׳¨׳©׳™׳׳× ׳™׳©׳™׳‘׳•׳× ׳׳”-HTML (׳›׳₪׳™ ׳©׳’׳™׳׳™׳ ׳• ׳‘׳“׳₪׳“׳₪׳)
    url = f"{COMPLOT_BASE}/yeshivot/#search/GetMeetingByDate&siteid={SITE_ID}&v=0&fd={fd}&td={td}&l=true&arguments=siteid,v,fd,td,l"
    try:
        r = session.get(f"{COMPLOT_BASE}/yeshivot/", timeout=15)
        soup = BeautifulSoup(r.text, "html.parser")

        # ׳—׳₪׳© ׳׳× ׳”׳ ׳×׳•׳ ׳™׳ ׳׳”-script ׳׳• ׳׳”-API ׳”׳₪׳ ׳™׳׳™
        # ׳ ׳¡׳” ׳׳× ׳”-API ׳”׳™׳“׳•׳¢
        api_url = f"{COMPLOT_BASE}/newengine/api/meetings/GetMeetingByDate?siteid={SITE_ID}&v=0&fd={fd}&td={td}&l=true"
        r2 = session.get(api_url, timeout=15)
        if r2.status_code == 200:
            try:
                data = r2.json()
                items = data if isinstance(data, list) else data.get("d", data.get("meetings", []))
                if items:
                    log(f"  API: {len(items)} ׳™׳©׳™׳‘׳•׳×")
                    return parse_api_meetings(items)
            except:
                pass
    except Exception as e:
        log(f"  ׳©׳’׳™׳׳”: {e}")

    # fallback: ׳ ׳¡׳” URL ׳™׳©׳™׳¨ ׳¢׳ ׳”׳₪׳¨׳׳˜׳¨׳™׳
    try:
        r3 = session.get(
            f"{COMPLOT_BASE}/newengine/Pages/meetings2.aspx",
            params={"siteid": SITE_ID, "fd": fd, "td": td},
            timeout=15
        )
        if r3.status_code == 200:
            return parse_html_meetings(r3.text, fd, td)
    except Exception as e:
        log(f"  fallback ׳©׳’׳™׳׳”: {e}")

    log("  ׳׳ ׳”׳¦׳׳—׳×׳™ ׳׳©׳׳•׳£ ׳™׳©׳™׳‘׳•׳×")
    return []

def parse_api_meetings(items):
    meetings = []
    for item in items:
        meetings.append({
            "meetingId":   str(item.get("MeetingId") or item.get("meetingId") or item.get("id","")),
            "committeeId": str(item.get("CommitteeId") or item.get("committeeId","")),
            "committee":   item.get("CommitteeName") or item.get("committeeName",""),
            "date":        item.get("MeetingDate") or item.get("date",""),
        })
    return meetings

def parse_html_meetings(html, fd, td):
    meetings = []
    soup = BeautifulSoup(html, "html.parser")
    for row in soup.select("tr"):
        cells = row.find_all("td")
        link  = row.find("a", href=re.compile(r"getMeeting"))
        if not link or len(cells) < 3: continue
        match = re.search(r"getMeeting\((\d+),(\d+)\)", link["href"])
        if not match: continue
        meetings.append({
            "meetingId":   match.group(2),
            "committeeId": match.group(1),
            "committee":   cells[1].get_text(strip=True),
            "date":        cells[2].get_text(strip=True),
        })
    return meetings

# ג”€ג”€ ׳©׳׳™׳₪׳× PDFs ׳©׳ ׳™׳©׳™׳‘׳” ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€
def fetch_meeting_pdfs(committee_id, meeting_id, committee, date):
    """׳©׳•׳׳£ ׳§׳™׳©׳•׳¨׳™ PDF ׳׳™׳©׳™׳‘׳” ׳¡׳₪׳¦׳™׳₪׳™׳×"""
    session = requests.Session()
    session.headers.update(HEADERS)

    try:
        # ׳›׳×׳•׳‘׳× ׳“׳£ ׳”׳™׳©׳™׳‘׳” (׳›׳₪׳™ ׳©׳’׳™׳׳™׳ ׳•)
        url = f"{COMPLOT_BASE}/yeshivot/#meeting/{committee_id}/{meeting_id}"
        # ׳”-API ׳”׳׳׳™׳×׳™ ׳©׳׳—׳–׳™׳¨ ׳׳× ׳׳¡׳׳›׳™ ׳”׳™׳©׳™׳‘׳”
        api_url = f"{COMPLOT_BASE}/newengine/api/meetings/GetMeetingDocuments?committeeId={committee_id}&meetingId={meeting_id}&siteid={SITE_ID}"

        r = session.get(api_url, timeout=15)
        if r.status_code == 200:
            try:
                docs = r.json()
                if isinstance(docs, list):
                    return [{"text": d.get("Title","׳׳¡׳׳"), "href": d.get("Url",""), "committee": committee, "date": date, "is_protocol": "׳₪׳¨׳•׳˜׳•׳§׳•׳" in d.get("Title","")} for d in docs if d.get("Url")]
            except: pass

        # fallback ג€“ HTML ׳™׳©׳™׳¨
        r2 = session.get(f"{COMPLOT_BASE}/yeshivot/", timeout=10)
        time.sleep(0.5)
        # ׳ ׳‘׳ ׳” URL ׳›׳׳• ׳©׳”-JS ׳¢׳•׳©׳”
        page_url = f"{COMPLOT_BASE}/yeshivot/?committee={committee_id}&meeting={meeting_id}"
        r3 = session.get(page_url, timeout=15)
        soup = BeautifulSoup(r3.text, "html.parser")
        pdfs = []
        for a in soup.find_all("a", href=re.compile(r"\.pdf", re.I)):
            href = a["href"]
            if not href.startswith("http"):
                href = COMPLOT_BASE + href
            pdfs.append({
                "text": a.get_text(strip=True) or "׳׳¡׳׳",
                "href": href,
                "committee": committee,
                "date": date,
                "is_protocol": "׳₪׳¨׳•׳˜׳•׳§׳•׳" in a.get_text()
            })
        return pdfs
    except Exception as e:
        log(f"  PDF ׳©׳’׳™׳׳” ({committee_id}/{meeting_id}): {e}")
        return []

# ג”€ג”€ ׳¡׳™׳›׳•׳ PDF ׳¢׳ Claude ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€
def summarize_pdf(pdf_url, committee, date):
    """׳׳•׳¨׳™׳“ PDF ׳•׳׳¡׳›׳ ׳¢׳ Claude API"""
    try:
        log(f"  ׳׳¡׳›׳ PDF: {pdf_url[-50:]}")
        r = requests.get(pdf_url, headers=HEADERS, timeout=30)
        if r.status_code != 200:
            log(f"  PDF ׳׳ ׳ ׳’׳™׳© (status {r.status_code})")
            return ""

        content_type = r.headers.get("Content-Type", "")
        if "pdf" not in content_type.lower() and not pdf_url.lower().endswith(".pdf"):
            log(f"  ׳׳ PDF: {content_type}")
            return ""

        pdf_b64 = base64.b64encode(r.content).decode()

        resp = requests.post(
            "https://api.anthropic.com/v1/messages",
            headers={"Content-Type": "application/json"},
            json={
                "model": "claude-sonnet-4-20250514",
                "max_tokens": 1000,
                "messages": [{
                    "role": "user",
                    "content": [
                        {
                            "type": "document",
                            "source": {"type": "base64", "media_type": "application/pdf", "data": pdf_b64}
                        },
                        {
                            "type": "text",
                            "text": f"׳¡׳›׳ ׳‘׳¢׳‘׳¨׳™׳× ׳׳× ׳”׳”׳—׳׳˜׳•׳× ׳”׳¢׳™׳§׳¨׳™׳•׳× ׳׳₪׳¨׳•׳˜׳•׳§׳•׳/׳׳¡׳׳ ׳–׳” ׳©׳ {committee} ׳׳×׳׳¨׳™׳ {date}. ׳›׳×׳•׳‘ ׳¢׳“ 6 ׳ ׳§׳•׳“׳•׳× ׳§׳¦׳¨׳•׳× ׳•׳׳¢׳©׳™׳•׳×. ׳׳ ׳–׳” ׳¡׳“׳¨ ׳™׳•׳ ׳•׳׳ ׳₪׳¨׳•׳˜׳•׳§׳•׳, ׳¦׳™׳™׳ ׳׳× ׳”׳ ׳•׳©׳׳™׳ ׳”׳¢׳™׳§׳¨׳™׳™׳ ׳©׳¢׳ ׳”׳₪׳¨׳§."
                        }
                    ]
                }]
            },
            timeout=60
        )

        if resp.status_code == 200:
            content = resp.json().get("content", [])
            summary = next((c["text"] for c in content if c.get("type") == "text"), "")
            log(f"  ׳¡׳•׳›׳ ׳‘׳”׳¦׳׳—׳” ({len(summary)} ׳×׳•׳•׳™׳)")
            return summary
        else:
            log(f"  Claude API ׳©׳’׳™׳׳”: {resp.status_code}")
            return ""

    except Exception as e:
        log(f"  ׳©׳’׳™׳׳× ׳¡׳™׳›׳•׳: {e}")
        return ""

# ג”€ג”€ ׳‘׳ ׳™׳™׳× ׳“׳•׳— HTML ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€
def build_html(meetings_with_docs, today_str):
    total_meetings = len(meetings_with_docs)
    total_pdfs     = sum(len(m["docs"]) for m in meetings_with_docs)
    total_protocols= sum(1 for m in meetings_with_docs for d in m["docs"] if d.get("is_protocol"))

    sections = ""
    for m in meetings_with_docs:
        docs_html = ""
        for d in m["docs"]:
            summary_html = ""
            if d.get("summary"):
                lines = d["summary"].replace("ג€¢","").strip().split("\n")
                bullets = "".join(f"<li>{l.strip().lstrip('- ג€¢*').strip()}</li>" for l in lines if l.strip())
                summary_html = f"<ul class='summary'>{bullets}</ul>"
            badge = "<span class='badge proto'>׳₪׳¨׳•׳˜׳•׳§׳•׳</span>" if d.get("is_protocol") else "<span class='badge agenda'>׳¡׳“׳¨ ׳™׳•׳</span>"
            docs_html += f"""
            <div class='doc'>
              <div class='doc-header'>
                {badge}
                <a href='{d["href"]}' target='_blank' class='doc-link'>{d["text"]}</a>
              </div>
              {summary_html}
            </div>"""

        if not docs_html:
            docs_html = "<p class='no-docs'>׳׳™׳ ׳׳¡׳׳›׳™׳ ׳–׳׳™׳ ׳™׳</p>"

        sections += f"""
        <section class='meeting-card'>
          <div class='meeting-header'>
            <span class='committee'>{m["committee"]}</span>
            <span class='date'>{m["date"]}</span>
          </div>
          {docs_html}
        </section>"""

    return f"""<!DOCTYPE html>
<html lang="he" dir="rtl">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>׳“׳•׳— ׳•׳¢׳“׳” ׳—׳™׳₪׳” ג€“ {today_str}</title>
<style>
@import url('https://fonts.googleapis.com/css2?family=Heebo:wght@300;400;600;800&display=swap');
:root{{
  --bg:#0e1117; --sf:#161b27; --br:#252d3d;
  --ac:#3b82f6; --gn:#22c55e; --yw:#eab308;
  --tx:#e2e8f0; --mt:#64748b;
}}
*{{box-sizing:border-box;margin:0;padding:0}}
body{{font-family:'Heebo',sans-serif;background:var(--bg);color:var(--tx);padding:24px 16px;max-width:860px;margin:0 auto}}
.header{{text-align:center;margin-bottom:32px}}
.header h1{{font-size:1.9rem;font-weight:800;color:#fff}}
.header p{{color:var(--mt);font-size:.88rem;margin-top:5px}}
.stats{{display:flex;gap:12px;flex-wrap:wrap;justify-content:center;margin-bottom:32px}}
.stat{{background:var(--sf);border:1px solid var(--br);border-radius:12px;
  padding:16px 22px;text-align:center;flex:1;min-width:110px}}
.stat .n{{font-size:1.9rem;font-weight:800;color:var(--ac)}}
.stat .l{{font-size:.72rem;color:var(--mt);margin-top:3px}}
.meeting-card{{background:var(--sf);border:1px solid var(--br);border-radius:14px;
  padding:20px;margin-bottom:18px}}
.meeting-header{{display:flex;justify-content:space-between;align-items:center;
  margin-bottom:14px;padding-bottom:12px;border-bottom:1px solid var(--br)}}
.committee{{font-weight:700;font-size:1rem;color:#fff}}
.date{{font-size:.82rem;color:var(--mt);background:#1e2535;
  padding:3px 10px;border-radius:6px}}
.doc{{background:#0e1522;border:1px solid #1e2d45;border-radius:10px;
  padding:14px;margin-bottom:10px}}
.doc:last-child{{margin-bottom:0}}
.doc-header{{display:flex;align-items:center;gap:10px;margin-bottom:8px}}
.badge{{font-size:.72rem;font-weight:700;padding:3px 9px;border-radius:999px}}
.badge.proto{{background:rgba(34,197,94,.15);color:var(--gn)}}
.badge.agenda{{background:rgba(59,130,246,.15);color:var(--ac)}}
.doc-link{{color:var(--ac);text-decoration:none;font-size:.88rem}}
.doc-link:hover{{text-decoration:underline}}
.summary{{padding-right:16px;margin-top:6px}}
.summary li{{font-size:.83rem;color:#94a3b8;margin-bottom:4px;line-height:1.5}}
.no-docs{{color:var(--mt);font-size:.82rem;font-style:italic}}
.footer{{text-align:center;color:var(--mt);font-size:.74rem;margin-top:28px}}
.footer a{{color:var(--ac)}}
</style>
</head>
<body>
<div class="header">
  <h1>נ—ן¸ ׳“׳•׳— ׳•׳¢׳“׳” ׳׳§׳•׳׳™׳× ג€“ ׳—׳™׳₪׳”</h1>
  <p>׳¢׳•׳“׳›׳: {today_str} | {CONFIG['days_back']} ׳™׳׳™׳ ׳׳—׳¨׳•׳ ׳™׳</p>
</div>
<div class="stats">
  <div class="stat"><div class="n">{total_meetings}</div><div class="l">׳™׳©׳™׳‘׳•׳×</div></div>
  <div class="stat"><div class="n">{total_pdfs}</div><div class="l">׳׳¡׳׳›׳™׳</div></div>
  <div class="stat"><div class="n">{total_protocols}</div><div class="l">׳₪׳¨׳•׳˜׳•׳§׳•׳׳™׳</div></div>
</div>
{sections if sections else '<p style="text-align:center;color:var(--mt)">׳׳ ׳ ׳׳¦׳׳• ׳™׳©׳™׳‘׳•׳× ׳‘׳×׳§׳•׳₪׳” ׳–׳•</p>'}
<div class="footer">
  <p><a href="https://haifa.complot.co.il/yeshivot/">Complot ׳—׳™׳₪׳”</a> ֲ· <a href="https://mavat.iplan.gov.il">׳׳‘׳"׳×</a></p>
  <p style="margin-top:5px">׳”׳“׳•׳— ׳”׳‘׳: ׳׳—׳¨ ׳‘-08:00 ׳׳•׳˜׳•׳׳˜׳™׳×</p>
</div>
</body></html>"""

# ג”€ג”€ ׳©׳׳™׳—׳× ׳׳™׳™׳ ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€
def send_email(subject, html):
    cfg = CONFIG["email"]
    if not cfg["enabled"] or not cfg["sender"]:
        log("׳׳™׳™׳ ׳׳ ׳׳•׳’׳“׳¨ ג€“ ׳׳“׳׳’")
        return
    try:
        msg = MIMEMultipart("alternative")
        msg["Subject"] = subject
        msg["From"]    = cfg["sender"]
        msg["To"]      = cfg["recipient"]
        msg.attach(MIMEText(html, "html", "utf-8"))
        with smtplib.SMTP(cfg["smtp_server"], cfg["smtp_port"]) as s:
            s.starttls()
            s.login(cfg["sender"], cfg["password"])
            s.sendmail(cfg["sender"], cfg["recipient"], msg.as_string())
        log("׳׳™׳™׳ ׳ ׳©׳׳—!")
    except Exception as e:
        log(f"׳©׳’׳™׳׳× ׳׳™׳™׳: {e}")

# ג”€ג”€ ׳¨׳׳©׳™ ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€
def main():
    CONFIG["data_dir"].mkdir(exist_ok=True)
    today_str = datetime.now().strftime("%d/%m/%Y %H:%M")
    log("=" * 50)
    log(f"׳“׳•׳— ׳™׳•׳׳™ ג€“ ׳•׳¢׳“׳” ׳׳§׳•׳׳™׳× ׳—׳™׳₪׳” v3")
    log(f"{today_str}")
    log("=" * 50)

    # 1. ׳©׳׳•׳£ ׳™׳©׳™׳‘׳•׳×
    meetings = fetch_meetings(CONFIG["days_back"])
    log(f"׳ ׳׳¦׳׳• {len(meetings)} ׳™׳©׳™׳‘׳•׳×")

    # 2. ׳©׳׳•׳£ PDFs ׳׳›׳ ׳™׳©׳™׳‘׳” ׳•׳¡׳›׳
    meetings_with_docs = []
    for m in meetings:
        log(f"׳™׳©׳™׳‘׳” {m['meetingId']} ג€“ {m['committee']} ({m['date']})")
        docs = fetch_meeting_pdfs(m["committeeId"], m["meetingId"], m["committee"], m["date"])
        log(f"  {len(docs)} ׳׳¡׳׳›׳™׳")

        # ׳¡׳›׳ ׳₪׳¨׳•׳˜׳•׳§׳•׳׳™׳
        for d in docs:
            if d.get("is_protocol") and d.get("href"):
                d["summary"] = summarize_pdf(d["href"], m["committee"], m["date"])
                time.sleep(1)

        meetings_with_docs.append({**m, "docs": docs})
        time.sleep(0.5)

    # 3. ׳‘׳ ׳” ׳“׳•׳—
    html = build_html(meetings_with_docs, today_str)
    CONFIG["report_html"].write_text(html, encoding="utf-8")
    log(f"׳“׳•׳— ׳ ׳©׳׳¨: {CONFIG['report_html']}")

    # 4. ׳©׳׳— ׳׳™׳™׳
    total_p = sum(1 for m in meetings_with_docs for d in m["docs"] if d.get("is_protocol"))
    subj = f"נ—ן¸ ׳“׳•׳— ׳•׳¢׳“׳” ׳—׳™׳₪׳” {datetime.now().strftime('%d/%m/%Y')} ג€“ {len(meetings)} ׳™׳©׳™׳‘׳•׳× | {total_p} ׳₪׳¨׳•׳˜׳•׳§׳•׳׳™׳"
    send_email(subj, html)
    log("׳¡׳™׳•׳!")

if __name__ == "__main__":
    main()
