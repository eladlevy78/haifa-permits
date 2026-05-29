#!/usr/bin/env python3
"""haifa_daily_digest.py v4 - ׳•׳¢׳“׳” ׳׳§׳•׳׳™׳× ׳—׳™׳₪׳”"""

import requests, json, os, time, smtplib, re, base64
from datetime import datetime, timedelta
from pathlib import Path
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.header import Header
from bs4 import BeautifulSoup

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

ARCHIVE_BASE = "https://archive.gis-net.co.il"
COMPLOT_BASE = "https://haifa.complot.co.il"

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/124.0 Safari/537.36",
    "Accept": "*/*",
    "Accept-Language": "he-IL,he;q=0.9",
}

def log(msg):
    ts = datetime.now().strftime("%H:%M:%S")
    print(f"[{ts}] {msg}")
    CONFIG["log_file"].parent.mkdir(exist_ok=True)
    with open(CONFIG["log_file"], "a", encoding="utf-8") as f:
        f.write(f"[{ts}] {msg}\n")

# ג”€ג”€ ׳©׳׳™׳₪׳× ׳™׳©׳™׳‘׳•׳× ׳“׳¨׳ ׳”-API ׳”׳™׳“׳•׳¢ ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€
def fetch_meetings(days_back=30):
    log("׳©׳•׳׳£ ׳™׳©׳™׳‘׳•׳× ׳-Complot...")
    today = datetime.now()
    fd    = (today - timedelta(days=days_back)).strftime("%d/%m/%Y")
    td    = today.strftime("%d/%m/%Y")

    # ׳”-API ׳”׳₪׳ ׳™׳׳™ ׳©׳’׳™׳׳™׳ ׳•
    apis = [
        f"{COMPLOT_BASE}/newengine/api/Meetings/GetMeetingByDate?siteid=16&v=0&fd={fd}&td={td}&l=true",
        f"{COMPLOT_BASE}/newengine/Services/MeetingsService.svc/json/GetMeetingByDate?siteid=16&v=0&fd={fd}&td={td}&l=true",
        f"{COMPLOT_BASE}/COMPLOTServices/MeetingsService.svc/GetMeetingByDate?siteid=16&fd={fd}&td={td}&v=0&l=true",
    ]

    session = requests.Session()
    session.headers.update(HEADERS)

    for url in apis:
        try:
            r = session.get(url, timeout=15)
            log(f"  {url[-60:]}: status={r.status_code}")
            if r.status_code == 200 and len(r.text) > 10:
                log(f"  ׳×׳’׳•׳‘׳”: {r.text[:200]}")
                try:
                    data = r.json()
                    items = data if isinstance(data, list) else \
                            data.get("d", data.get("GetMeetingByDateResult", data.get("meetings", [])))
                    if items:
                        log(f"  ׳ ׳׳¦׳׳• {len(items)} ׳™׳©׳™׳‘׳•׳×!")
                        return [parse_meeting(i) for i in items]
                except Exception as e:
                    log(f"  JSON ׳©׳’׳™׳׳”: {e}, text: {r.text[:100]}")
        except Exception as e:
            log(f"  ׳©׳’׳™׳׳”: {e}")
        time.sleep(0.5)

    log("  Complot ׳—׳¡׳•׳ ג€“ ׳׳—׳–׳™׳¨ ׳¨׳©׳™׳׳” ׳™׳“׳ ׳™׳×")
    return get_hardcoded_meetings(days_back)

def parse_meeting(item):
    return {
        "meetingId":   str(item.get("MeetingId") or item.get("meetingId") or item.get("Id","")),
        "committeeId": str(item.get("CommitteeId") or item.get("committeeId","")),
        "committee":   item.get("CommitteeName") or item.get("committeeName",""),
        "date":        item.get("MeetingDate") or item.get("MeetingDateStr") or item.get("date",""),
    }

def get_hardcoded_meetings(days_back):
    """׳™׳©׳™׳‘׳•׳× ׳™׳“׳•׳¢׳•׳× ׳©׳’׳™׳׳™׳ ׳• ׳‘׳“׳₪׳“׳₪׳ ג€“ fallback"""
    today = datetime.now()
    cutoff = today - timedelta(days=days_back)
    all_meetings = [
        {"meetingId":"675","committeeId":"7","committee":"׳¨׳©׳•׳× ׳¨׳™׳©׳•׳™ ׳׳§׳•׳׳™׳×","date":"24/05/2026"},
        {"meetingId":"151","committeeId":"4","committee":"׳•׳¢׳“׳” ׳׳©׳™׳׳•׳¨ ׳׳‘׳ ׳™׳ ׳•׳׳×׳¨׳™׳","date":"24/05/2026"},
        {"meetingId":"62", "committeeId":"3","committee":"׳•׳¢׳“׳× ׳׳©׳ ׳” ׳©׳ ׳”׳•׳¢׳“׳” ׳”׳׳§׳•׳׳™׳×","date":"18/05/2026"},
        {"meetingId":"674","committeeId":"7","committee":"׳¨׳©׳•׳× ׳¨׳™׳©׳•׳™ ׳׳§׳•׳׳™׳×","date":"14/05/2026"},
        {"meetingId":"61", "committeeId":"3","committee":"׳•׳¢׳“׳× ׳׳©׳ ׳” ׳©׳ ׳”׳•׳¢׳“׳” ׳”׳׳§׳•׳׳™׳×","date":"11/05/2026"},
        {"meetingId":"673","committeeId":"7","committee":"׳¨׳©׳•׳× ׳¨׳™׳©׳•׳™ ׳׳§׳•׳׳™׳×","date":"06/05/2026"},
        {"meetingId":"60", "committeeId":"3","committee":"׳•׳¢׳“׳× ׳׳©׳ ׳” ׳©׳ ׳”׳•׳¢׳“׳” ׳”׳׳§׳•׳׳™׳×","date":"27/04/2026"},
        {"meetingId":"672","committeeId":"7","committee":"׳¨׳©׳•׳× ׳¨׳™׳©׳•׳™ ׳׳§׳•׳׳™׳×","date":"26/04/2026"},
        {"meetingId":"671","committeeId":"7","committee":"׳¨׳©׳•׳× ׳¨׳™׳©׳•׳™ ׳׳§׳•׳׳™׳×","date":"13/04/2026"},
    ]
    result = []
    for m in all_meetings:
        try:
            d = datetime.strptime(m["date"], "%d/%m/%Y")
            if d >= cutoff:
                result.append(m)
        except:
            result.append(m)
    log(f"  fallback: {len(result)} ׳™׳©׳™׳‘׳•׳×")
    return result

# ג”€ג”€ ׳©׳׳™׳₪׳× PDFs ׳׳›׳ ׳™׳©׳™׳‘׳” ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€
def fetch_meeting_pdfs(committee_id, meeting_id, committee, date):
    log(f"  Fetching docs for meeting {meeting_id}...")

    # Try API first
    session = requests.Session()
    session.headers.update(HEADERS)
    for url in [
        f"{COMPLOT_BASE}/newengine/api/Meetings/GetMeetingDocuments?committeeId={committee_id}&meetingId={meeting_id}&siteid=16",
        f"{COMPLOT_BASE}/newengine/Services/MeetingsService.svc/json/GetMeetingDocuments?committeeId={committee_id}&meetingId={meeting_id}&siteid=16",
    ]:
        try:
            r = session.get(url, timeout=15)
            if r.status_code == 200 and len(r.text) > 5:
                docs = r.json()
                if isinstance(docs, list) and docs:
                    log(f"    {len(docs)} docs from API")
                    return [format_doc(d, committee, date) for d in docs]
        except:
            pass

    # Fallback: hardcoded PDFs discovered via Chrome browser session
    hardcoded = {
        "675": [
            {"text": "Agenda - Local Licensing Authority", "href": "https://archive.gis-net.co.il/Haifa/Pirsumim/951/e829597a-b0e6-4789-9194-19206ecf6089.pdf", "is_protocol": False},
            {"text": "Protocol - Local Licensing Authority", "href": "https://archive.gis-net.co.il/Haifa/Pirsumim/778/c3111d4b-3844-4354-8646-98c3193e884d.pdf", "is_protocol": True},
        ],
        "151": [
            {"text": "Agenda - Historic Preservation Committee", "href": "https://archive.gis-net.co.il/Haifa/Pirsumim/951/6a69298e-8eba-40fc-8495-47a3db5a5895.pdf", "is_protocol": False},
        ],
        "62": [
            {"text": "Agenda - Sub-Committee 62", "href": "https://archive.gis-net.co.il/Haifa/Pirsumim/951/0013b341-4800-449d-aed2-f5e04e512fa7.pdf", "is_protocol": False},
            {"text": "Addendum - Sub-Committee 62", "href": "https://archive.gis-net.co.il/Haifa/Pirsumim/951/acb965b2-7f6f-45a5-911f-e71fc861089c.pdf", "is_protocol": False},
        ],
        "674": [
            {"text": "Agenda - Local Licensing Authority", "href": "https://archive.gis-net.co.il/Haifa/Pirsumim/951/7fbc7bcc-97df-4791-8c66-2c30b14d2aba.pdf", "is_protocol": False},
            {"text": "Protocol - Local Licensing Authority", "href": "https://archive.gis-net.co.il/Haifa/Pirsumim/778/362054d5-1e90-4269-8680-7e7905abe3fe.pdf", "is_protocol": True},
        ],
        "673": [
            {"text": "Protocol - Local Licensing Authority", "href": "https://archive.gis-net.co.il/Haifa/Pirsumim/778/6ea1d4ff-4fce-48ea-842d-02391b4c142e.pdf", "is_protocol": True},
        ],
    }

    if meeting_id in hardcoded:
        docs = [{**d, "committee": committee, "date": date} for d in hardcoded[meeting_id]]
        log(f"    {len(docs)} docs from hardcoded list")
        return docs

    log(f"    No docs for meeting {meeting_id}")
    return []

def format_doc(d, committee, date):
    title = d.get("Title") or d.get("DocumentName") or d.get("title","׳׳¡׳׳")
    url   = d.get("Url") or d.get("DocumentUrl") or d.get("url","")
    if url and not url.startswith("http"):
        url = COMPLOT_BASE + url
    return {
        "text": title,
        "href": url,
        "committee": committee,
        "date": date,
        "is_protocol": "׳₪׳¨׳•׳˜׳•׳§׳•׳" in title
    }

# ג”€ג”€ ׳¡׳™׳›׳•׳ PDF ׳¢׳ Claude ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€
def summarize_pdf(pdf_url, committee, date):
    if not pdf_url or not pdf_url.startswith("http"):
        return ""
    try:
        log(f"    ׳׳¡׳›׳: {pdf_url[-50:]}")
        r = requests.get(pdf_url, headers=HEADERS, timeout=30)
        if r.status_code != 200: return ""
        pdf_b64 = base64.b64encode(r.content).decode()
        resp = requests.post(
            "https://api.anthropic.com/v1/messages",
            headers={"Content-Type": "application/json"},
            json={
                "model": "claude-sonnet-4-20250514",
                "max_tokens": 800,
                "messages": [{"role":"user","content":[
                    {"type":"document","source":{"type":"base64","media_type":"application/pdf","data":pdf_b64}},
                    {"type":"text","text":f"׳¡׳›׳ ׳‘׳¢׳‘׳¨׳™׳× ׳׳× ׳”׳”׳—׳׳˜׳•׳× ׳”׳¢׳™׳§׳¨׳™׳•׳× ׳׳₪׳¨׳•׳˜׳•׳§׳•׳ ׳™׳©׳™׳‘׳× {committee} ׳-{date}. ׳›׳×׳•׳‘ ׳¢׳“ 6 ׳ ׳§׳•׳“׳•׳× ׳§׳¦׳¨׳•׳×."}
                ]}]
            },
            timeout=60
        )
        if resp.status_code == 200:
            c = resp.json().get("content",[])
            return next((x["text"] for x in c if x.get("type")=="text"),"")
    except Exception as e:
        log(f"    ׳©׳’׳™׳׳× ׳¡׳™׳›׳•׳: {e}")
    return ""

# ג”€ג”€ HTML ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€
def build_html(meetings_with_docs, today_str):
    total_m = len(meetings_with_docs)
    total_d = sum(len(m["docs"]) for m in meetings_with_docs)
    total_p = sum(1 for m in meetings_with_docs for d in m["docs"] if d.get("is_protocol"))

    sections = ""
    for m in meetings_with_docs:
        docs_html = ""
        for d in m["docs"]:
            badge   = "<span class='bp'>׳₪׳¨׳•׳˜׳•׳§׳•׳</span>" if d.get("is_protocol") else "<span class='ba'>׳¡׳“׳¨ ׳™׳•׳</span>"
            summary = ""
            if d.get("summary"):
                lines   = [l.strip().lstrip("-ג€¢* ") for l in d["summary"].split("\n") if l.strip()]
                bullets = "".join(f"<li>{l}</li>" for l in lines)
                summary = f"<ul class='sm'>{bullets}</ul>"
            href = d.get("href","#")
            docs_html += f"<div class='doc'><div class='dh'>{badge}<a href='{href}' target='_blank' class='dl'>{d['text']}</a></div>{summary}</div>"
        if not docs_html:
            docs_html = "<p class='nd'>׳׳™׳ ׳׳¡׳׳›׳™׳ ׳–׳׳™׳ ׳™׳</p>"

        sections += f"""<section class='mc'>
  <div class='mh'><span class='cm'>{m['committee']}</span><span class='dt'>{m['date']}</span></div>
  {docs_html}
</section>"""

    empty = "<p style='text-align:center;color:#64748b;padding:40px'>׳׳ ׳ ׳׳¦׳׳• ׳™׳©׳™׳‘׳•׳× ׳‘׳×׳§׳•׳₪׳” ׳–׳•</p>"
    return f"""<!DOCTYPE html>
<html lang="he" dir="rtl">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>׳“׳•׳— ׳•׳¢׳“׳” ׳—׳™׳₪׳” {today_str}</title>
<style>
@import url('https://fonts.googleapis.com/css2?family=Heebo:wght@300;400;600;800&display=swap');
:root{{--bg:#0e1117;--sf:#161b27;--br:#252d3d;--ac:#3b82f6;--gn:#22c55e;--tx:#e2e8f0;--mt:#64748b}}
*{{box-sizing:border-box;margin:0;padding:0}}
body{{font-family:'Heebo',sans-serif;background:var(--bg);color:var(--tx);padding:24px 16px;max-width:820px;margin:0 auto}}
.hd{{text-align:center;margin-bottom:28px}}
.hd h1{{font-size:1.8rem;font-weight:800;color:#fff}}
.hd p{{color:var(--mt);font-size:.85rem;margin-top:5px}}
.st{{display:flex;gap:12px;flex-wrap:wrap;justify-content:center;margin-bottom:28px}}
.sc{{background:var(--sf);border:1px solid var(--br);border-radius:12px;padding:14px 20px;text-align:center;flex:1;min-width:100px}}
.sc .n{{font-size:1.8rem;font-weight:800;color:var(--ac)}}
.sc .l{{font-size:.7rem;color:var(--mt);margin-top:3px}}
.mc{{background:var(--sf);border:1px solid var(--br);border-radius:14px;padding:18px;margin-bottom:16px}}
.mh{{display:flex;justify-content:space-between;align-items:center;margin-bottom:12px;padding-bottom:10px;border-bottom:1px solid var(--br)}}
.cm{{font-weight:700;font-size:.98rem}}
.dt{{font-size:.8rem;color:var(--mt);background:#1e2535;padding:3px 9px;border-radius:6px}}
.doc{{background:#0e1522;border:1px solid #1e2d45;border-radius:10px;padding:12px;margin-bottom:8px}}
.doc:last-child{{margin-bottom:0}}
.dh{{display:flex;align-items:center;gap:8px}}
.bp,.ba{{font-size:.7rem;font-weight:700;padding:2px 8px;border-radius:999px;white-space:nowrap}}
.bp{{background:rgba(34,197,94,.15);color:#22c55e}}
.ba{{background:rgba(59,130,246,.15);color:#3b82f6}}
.dl{{color:#3b82f6;text-decoration:none;font-size:.86rem}}
.dl:hover{{text-decoration:underline}}
.sm{{padding-right:14px;margin-top:8px}}
.sm li{{font-size:.81rem;color:#94a3b8;margin-bottom:3px;line-height:1.5}}
.nd{{color:var(--mt);font-size:.8rem;font-style:italic;padding:4px 0}}
.ft{{text-align:center;color:var(--mt);font-size:.72rem;margin-top:24px}}
.ft a{{color:#3b82f6}}
</style>
</head>
<body>
<div class="hd"><h1>נ—ן¸ ׳“׳•׳— ׳•׳¢׳“׳” ׳׳§׳•׳׳™׳× ג€“ ׳—׳™׳₪׳”</h1><p>׳¢׳•׳“׳›׳: {today_str} | {CONFIG['days_back']} ׳™׳׳™׳ ׳׳—׳¨׳•׳ ׳™׳</p></div>
<div class="st">
  <div class="sc"><div class="n">{total_m}</div><div class="l">׳™׳©׳™׳‘׳•׳×</div></div>
  <div class="sc"><div class="n">{total_d}</div><div class="l">׳׳¡׳׳›׳™׳</div></div>
  <div class="sc"><div class="n">{total_p}</div><div class="l">׳₪׳¨׳•׳˜׳•׳§׳•׳׳™׳</div></div>
</div>
{sections or empty}
<div class="ft">
  <p><a href="https://haifa.complot.co.il/yeshivot/">Complot ׳—׳™׳₪׳”</a> ֲ· <a href="https://mavat.iplan.gov.il">׳׳‘׳"׳×</a></p>
  <p style="margin-top:5px">׳”׳“׳•׳— ׳”׳‘׳: ׳׳—׳¨ ׳‘-08:00</p>
</div>
</body></html>"""

# ג”€ג”€ ׳׳™׳™׳ ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€
def send_email(subject, html):
    cfg = CONFIG["email"]
    if not cfg["enabled"] or not cfg["sender"]:
        log("׳׳™׳™׳ ׳׳ ׳׳•׳’׳“׳¨")
        return
    try:
        from email.mime.base import MIMEBase
        from email import encoders as email_encoders
        msg = MIMEMultipart("alternative")
        msg["Subject"] = Header(subject, "utf-8")
        msg["From"]    = cfg["sender"]
        msg["To"]      = cfg["recipient"]
        html_bytes = html.encode("utf-8")
        part = MIMEBase("text", "html", charset="utf-8")
        part.set_payload(html_bytes)
        email_encoders.encode_base64(part)
        part.add_header("Content-Transfer-Encoding", "base64")
        msg.attach(part)
        with smtplib.SMTP(cfg["smtp_server"], cfg["smtp_port"]) as s:
            s.starttls()
            s.login(cfg["sender"], cfg["password"])
            s.send_message(msg)
        log("Email sent!")
    except Exception as e:
        log(f"׳©׳’׳™׳׳× ׳׳™׳™׳: {e}")

# ג”€ג”€ ׳¨׳׳©׳™ ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€ג”€
def main():
    CONFIG["data_dir"].mkdir(exist_ok=True)
    today_str = datetime.now().strftime("%d/%m/%Y %H:%M")
    log("=" * 50)
    log(f"׳“׳•׳— ׳™׳•׳׳™ v4 ג€“ ׳•׳¢׳“׳” ׳׳§׳•׳׳™׳× ׳—׳™׳₪׳”")
    log(today_str)
    log("=" * 50)

    meetings = fetch_meetings(CONFIG["days_back"])
    log(f"׳¡׳”\"׳› {len(meetings)} ׳™׳©׳™׳‘׳•׳×")

    meetings_with_docs = []
    for m in meetings:
        log(f"׳™׳©׳™׳‘׳” {m['meetingId']} ג€“ {m['committee']} ({m['date']})")
        docs = fetch_meeting_pdfs(m["committeeId"], m["meetingId"], m["committee"], m["date"])
        for d in docs:
            if d.get("is_protocol") and d.get("href","#") != "#":
                d["summary"] = summarize_pdf(d["href"], m["committee"], m["date"])
                time.sleep(1)
        meetings_with_docs.append({**m, "docs": docs})
        time.sleep(0.5)

    html = build_html(meetings_with_docs, today_str)
    CONFIG["report_html"].write_text(html, encoding="utf-8")
    log(f"׳“׳•׳— ׳ ׳©׳׳¨")

    total_p = sum(1 for m in meetings_with_docs for d in m["docs"] if d.get("is_protocol"))
    subj = f"׳“׳•׳— ׳•׳¢׳“׳” ׳—׳™׳₪׳” {datetime.now().strftime('%d/%m/%Y')} ג€“ {len(meetings)} ׳™׳©׳™׳‘׳•׳× | {total_p} ׳₪׳¨׳•׳˜׳•׳§׳•׳׳™׳"
    send_email(subj, html)
    log("׳¡׳™׳•׳!")

if __name__ == "__main__":
    main()
