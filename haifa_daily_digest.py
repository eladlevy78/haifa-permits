#!/usr/bin/env python3
"""haifa_daily_digest.py v5 - Haifa Local Committee Weekly Email"""

import requests, json, os, smtplib, base64
from datetime import datetime
from pathlib import Path
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.header import Header

CONFIG = {
    "data_dir":    Path("./haifa_data"),
    "report_html": Path("./haifa_data/daily_report.html"),
    "log_file":    Path("./haifa_data/digest.log"),
    "email": {
        "enabled":   True,
        "smtp_server": "smtp.gmail.com",
        "smtp_port":   587,
        "sender":    os.environ.get("EMAIL_SENDER", ""),
        "password":  os.environ.get("EMAIL_PASSWORD", ""),
        "recipient": os.environ.get("EMAIL_RECIPIENT", ""),
    }
}

GITHUB_REPO = "eladlevy78/haifa-permits"
GITHUB_TOKEN = os.environ.get("PAT_TOKEN", "")

def log(msg):
    ts = datetime.now().strftime("%H:%M:%S")
    print(f"[{ts}] {msg}")
    CONFIG["log_file"].parent.mkdir(exist_ok=True)
    with open(CONFIG["log_file"], "a") as f:
        f.write(f"[{ts}] {msg}\n")

def fetch_summaries():
    """Fetch summaries.json from GitHub repo"""
    log("Fetching summaries from GitHub...")
    try:
        url = f"https://api.github.com/repos/{GITHUB_REPO}/contents/summaries.json"
        headers = {"Accept": "application/vnd.github.v3+json"}
        if GITHUB_TOKEN:
            headers["Authorization"] = f"Bearer {GITHUB_TOKEN}"
        r = requests.get(url, headers=headers, timeout=15)
        if r.status_code == 200:
            data = r.json()
            content = base64.b64decode(data["content"]).decode("utf-8")
            summaries = json.loads(content)
            log(f"  Found {len(summaries.get('meetings', []))} meetings")
            return summaries
        else:
            log(f"  No summaries.json found (status {r.status_code})")
            return None
    except Exception as e:
        log(f"  Error: {e}")
        return None

def build_html(summaries):
    today_str = datetime.now().strftime("%d/%m/%Y %H:%M")
    
    if not summaries:
        return build_no_summaries_html(today_str)
    
    period = summaries.get("period", {})
    meetings = summaries.get("meetings", [])
    generated = summaries.get("generated", "")
    
    total_meetings  = len(meetings)
    total_protocols = sum(1 for m in meetings for d in m.get("docs",[]) if d.get("isProtocol"))
    total_docs      = sum(len(m.get("docs",[])) for m in meetings)

    meeting_cards = ""
    for m in meetings:
        docs_html = ""
        for d in m.get("docs", []):
            badge   = "<span class='bp'>Protocol</span>" if d.get("isProtocol") else "<span class='ba'>Agenda</span>"
            summary = ""
            if d.get("summary"):
                lines   = [l.strip().lstrip("-ג€¢* ") for l in d["summary"].split("\n") if l.strip()]
                bullets = "".join(f"<li>{l}</li>" for l in lines)
                summary = f"<ul class='sm'>{bullets}</ul>"
            docs_html += f"""
            <div class='doc'>
              <div class='dh'>{badge} <a href='{d.get("href","#")}' target='_blank' class='dl'>{d.get("text","Document")}</a></div>
              {summary}
            </div>"""

        if not docs_html:
            docs_html = "<p class='nd'>No documents available</p>"

        meeting_cards += f"""
        <section class='mc'>
          <div class='mh'>
            <span class='cm'>{m.get("committee","")}</span>
            <span class='dt'>{m.get("date","")}</span>
          </div>
          {docs_html}
        </section>"""

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>Haifa Committee Report {today_str}</title>
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;600;800&display=swap');
:root{{--bg:#0e1117;--sf:#161b27;--br:#252d3d;--ac:#3b82f6;--gn:#22c55e;--tx:#e2e8f0;--mt:#64748b}}
*{{box-sizing:border-box;margin:0;padding:0}}
body{{font-family:'Inter',sans-serif;background:var(--bg);color:var(--tx);padding:24px 16px;max-width:820px;margin:0 auto}}
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
.sm{{padding-left:16px;margin-top:8px}}
.sm li{{font-size:.82rem;color:#94a3b8;margin-bottom:4px;line-height:1.5}}
.nd{{color:var(--mt);font-size:.8rem;font-style:italic}}
.ft{{text-align:center;color:var(--mt);font-size:.72rem;margin-top:24px}}
.ft a{{color:#3b82f6}}
.period{{background:rgba(59,130,246,.1);border:1px solid rgba(59,130,246,.3);border-radius:8px;padding:8px 14px;text-align:center;margin-bottom:24px;font-size:.82rem;color:#94a3b8}}
</style>
</head>
<body>
<div class="hd">
  <h1>נ—ן¸ Haifa Local Committee Report</h1>
  <p>Generated: {today_str}</p>
</div>
<div class="period">
  Weekly summary: {period.get("from","")} ג€“ {period.get("to","")}
</div>
<div class="st">
  <div class="sc"><div class="n">{total_meetings}</div><div class="l">Meetings</div></div>
  <div class="sc"><div class="n">{total_docs}</div><div class="l">Documents</div></div>
  <div class="sc"><div class="n">{total_protocols}</div><div class="l">Protocols</div></div>
</div>
{meeting_cards}
<div class="ft">
  <p><a href="https://haifa.complot.co.il/yeshivot/">Complot Haifa</a> ֲ· <a href="https://mavat.iplan.gov.il">iplan.gov.il</a></p>
  <p style="margin-top:5px">Next report: Friday at 08:00</p>
</div>
</body></html>"""

def build_no_summaries_html(today_str):
    return f"""<!DOCTYPE html>
<html lang="en">
<head><meta charset="UTF-8"><title>Haifa Committee Report</title>
<style>body{{font-family:Inter,sans-serif;background:#0e1117;color:#e2e8f0;padding:40px;text-align:center}}</style>
</head>
<body>
<h1>נ—ן¸ Haifa Local Committee Report</h1>
<p style="color:#64748b;margin-top:20px">No summaries available yet.</p>
<p style="color:#64748b;margin-top:10px">Run the Chrome weekly summary script on Friday morning to generate summaries.</p>
</body></html>"""

def send_email(subject, html):
    cfg = CONFIG["email"]
    if not cfg["enabled"] or not cfg["sender"]:
        log("Email not configured")
        return
    try:
        msg = MIMEMultipart("alternative")
        msg["Subject"] = Header(subject, "utf-8")
        msg["From"]    = cfg["sender"]
        msg["To"]      = cfg["recipient"]
        msg.attach(MIMEText(html, "html", "utf-8"))
        with smtplib.SMTP(cfg["smtp_server"], cfg["smtp_port"]) as s:
            s.starttls()
            s.login(cfg["sender"], cfg["password"])
            s.send_message(msg)
        log("Email sent!")
    except Exception as e:
        log(f"Email error: {e}")

def main():
    CONFIG["data_dir"].mkdir(exist_ok=True)
    today_str = datetime.now().strftime("%d/%m/%Y %H:%M")
    log("=" * 50)
    log("Haifa Committee Weekly Digest v5")
    log(today_str)
    log("=" * 50)

    summaries = fetch_summaries()
    html = build_html(summaries)
    CONFIG["report_html"].write_text(html, encoding="utf-8")
    log("Report saved")

    if summaries:
        meetings = summaries.get("meetings", [])
        protocols = sum(1 for m in meetings for d in m.get("docs",[]) if d.get("isProtocol"))
        period = summaries.get("period", {})
        subj = f"Haifa Committee Report {period.get('from','')} - {period.get('to','')} | {len(meetings)} meetings | {protocols} protocols"
    else:
        subj = f"Haifa Committee Report {datetime.now().strftime('%d/%m/%Y')} - No summaries yet"

    send_email(subj, html)
    log("Done!")

if __name__ == "__main__":
    main()
