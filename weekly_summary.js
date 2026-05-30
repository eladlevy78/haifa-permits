/**
 * weekly_summary.js  —  Haifa Permit Digest
 * 
 * HOW TO RUN:
 *   1. Start proxy:  set ANTHROPIC_API_KEY=sk-ant-...  then  node claude_proxy.js
 *   2. Open Chrome on https://haifa.complot.co.il/yeshivot/
 *   3. Set the date range and click הצג to load meetings
 *   4. Open DevTools Console and paste this entire script
 *
 * WHAT IT DOES:
 *   - Reads meetings directly from the rendered table on screen
 *   - For each meeting, navigates to its archive page and finds all documents
 *   - Fetches each document via the site's own internal API (same origin, no CORS)
 *   - Extracts text using pdf.js
 *   - Sends text to local Claude proxy for summarization
 *   - Pushes summaries.json to GitHub
 */

(async () => {

  // ── CONFIG ────────────────────────────────────────────────────────────────
  const GITHUB_TOKEN  = "YOUR_GITHUB_TOKEN_HERE";   // ← replace with ghp_...
  const GITHUB_REPO   = "eladlevy78/haifa-permits";
  const GITHUB_BRANCH = "main";
  const PROXY_URL     = "http://localhost:3131/summarize";

  // Only summarize protocol documents (פרוטוקול), skip agenda (סדר יום)
  // Set to false to summarize all documents
  const PROTOCOL_ONLY = true;

  // ── HELPERS ───────────────────────────────────────────────────────────────
  function log(msg) { console.log(`[haifa] ${msg}`); }
  function formatDate(d) { return d.toISOString().split("T")[0]; }
  function sleep(ms) { return new Promise(r => setTimeout(r, ms)); }

  // Build the internal Complot document URL (same origin — no CORS)
  function buildDocUrl(t, m, r) {
    const base = xpaBaseURL; // already defined by the page
    const siteId = getSiteId(); // already defined by the page
    return `/${base}GetGilyonDrishot&siteid=${siteId}&t=${t}&m=${m}&r=${r}&arguments=siteid,t,m,r`;
  }

  // ── STEP 1: LOAD PDF.JS ───────────────────────────────────────────────────
  async function loadPdfJs() {
    if (window.pdfjsLib) return window.pdfjsLib;
    log("Loading pdf.js...");
    await new Promise((resolve, reject) => {
      const s = document.createElement("script");
      s.src = "https://cdnjs.cloudflare.com/ajax/libs/pdf.js/3.11.174/pdf.min.js";
      s.onload = resolve;
      s.onerror = reject;
      document.head.appendChild(s);
    });
    window.pdfjsLib.GlobalWorkerOptions.workerSrc =
      "https://cdnjs.cloudflare.com/ajax/libs/pdf.js/3.11.174/pdf.worker.min.js";
    log("pdf.js ready ✓");
    return window.pdfjsLib;
  }

  // ── STEP 2: SCRAPE MEETINGS FROM THE CURRENT TABLE ───────────────────────
  function scrapeMeetingsFromTable() {
    const rows = document.querySelectorAll("#results-table tbody tr");
    const meetings = [];
    rows.forEach(row => {
      const cells = row.querySelectorAll("td");
      if (cells.length < 4) return;

      // Extract meeting ID from the onclick of the archive button
      const archiveBtn = row.querySelector("a[href*='getMeeting'], a[aria-label*='הישיבה']");
      let meetingId = null;
      if (archiveBtn) {
        const match = archiveBtn.href.match(/getMeeting\((\d+),(\d+)\)/);
        if (match) meetingId = match[2];
      }
      // Fallback: get from cell text
      if (!meetingId) {
        const idCell = cells[1];
        if (idCell) meetingId = idCell.innerText.trim();
      }

      const type = cells[2] ? cells[2].innerText.trim() : "";
      const date = cells[3] ? cells[3].innerText.trim() : "";

      if (meetingId) {
        meetings.push({ id: meetingId, type, date, t: 7 });
      }
    });
    log(`Scraped ${meetings.length} meetings from table`);
    return meetings;
  }

  // ── STEP 3: GET DOCUMENT IDs FOR A MEETING ───────────────────────────────
  async function getDocumentsForMeeting(meeting) {
    // Navigate to the meeting archive page
    location.hash = `#meeting/${meeting.t}/${meeting.id}`;
    await sleep(2500); // wait for page to load

    // Find all document buttons with showRishuyDrishot onclick
    const docButtons = document.querySelectorAll("[onclick*='showRishuyDrishot']");
    const docs = [];

    docButtons.forEach(btn => {
      const onclick = btn.getAttribute("onclick");
      const match = onclick.match(/showRishuyDrishot\((\d+),(\d+),(\d+)/);
      if (!match) return;

      // Get document label from nearby text
      const row = btn.closest("tr");
      let label = "";
      if (row) {
        const cells = row.querySelectorAll("td");
        cells.forEach(c => { if (c.innerText.trim().length > 2) label += c.innerText.trim() + " "; });
      }
      label = label.trim();

      // Filter to protocol only if configured
      if (PROTOCOL_ONLY && !label.includes("פרוטוקול")) return;

      docs.push({
        t: match[1],
        m: match[2],
        r: match[3],
        label
      });
    });

    log(`  Meeting ${meeting.id}: found ${docs.length} document(s)`);
    return docs;
  }

  // ── STEP 4: FETCH AND EXTRACT PDF TEXT ───────────────────────────────────
  async function extractTextFromDoc(doc) {
    const lib = await loadPdfJs();
    const url = buildDocUrl(doc.t, doc.m, doc.r);
    log(`  Fetching: ${url.slice(0, 80)}...`);

    try {
      // Fetch the document page to find the actual PDF link
      const res = await fetch(url, { credentials: "include" });
      const html = await res.text();

      // Look for PDF URL in the response
      const pdfMatch = html.match(/href=["']([^"']*\.pdf[^"']*)/i) ||
                       html.match(/src=["']([^"']*\.pdf[^"']*)/i) ||
                       html.match(/(https?:\/\/[^"'\s]+\.pdf)/i);

      let pdfUrl = null;
      if (pdfMatch) {
        pdfUrl = pdfMatch[1];
        if (!pdfUrl.startsWith("http")) {
          pdfUrl = "https://haifa.complot.co.il" + pdfUrl;
        }
        log(`  Found PDF: ${pdfUrl.slice(0, 80)}`);
      } else {
        // The response itself might be a PDF
        const contentType = res.headers.get("content-type") || "";
        if (contentType.includes("pdf")) {
          pdfUrl = url;
          log(`  Response is PDF directly`);
        } else {
          // Try fetching again as array buffer and check magic bytes
          log(`  No PDF link found in HTML, trying direct fetch...`);
          const buf = await (await fetch(url, { credentials: "include" })).arrayBuffer();
          const bytes = new Uint8Array(buf.slice(0, 4));
          const isPdf = bytes[0] === 0x25 && bytes[1] === 0x50; // %P
          if (isPdf) {
            // Convert to blob URL for pdf.js
            const blob = new Blob([buf], { type: "application/pdf" });
            pdfUrl = URL.createObjectURL(blob);
          }
        }
      }

      if (!pdfUrl) {
        log(`  ⚠️ Could not locate PDF`);
        return null;
      }

      // Extract text with pdf.js
      const pdf = await lib.getDocument({ url: pdfUrl, withCredentials: true }).promise;
      let text = "";
      for (let p = 1; p <= Math.min(pdf.numPages, 40); p++) {
        const page = await pdf.getPage(p);
        const content = await page.getTextContent();
        text += content.items.map(i => i.str).join(" ") + "\n";
      }
      return text.trim();

    } catch (err) {
      log(`  ❌ Extract failed: ${err.message}`);
      return null;
    }
  }

  // ── STEP 5: SUMMARIZE VIA LOCAL PROXY ────────────────────────────────────
  async function summarize(pdfText, meetingTitle, meetingDate) {
    log(`  Calling Claude...`);
    try {
      const res = await fetch(PROXY_URL, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ pdfText, meetingTitle, meetingDate })
      });
      if (!res.ok) {
        log(`  ⚠️ Proxy returned ${res.status}`);
        return null;
      }
      const data = await res.json();
      return data.summary || null;
    } catch (err) {
      log(`  ❌ Proxy unreachable: ${err.message}`);
      log(`     Make sure claude_proxy.js is running!`);
      return null;
    }
  }

  // ── STEP 6: PUSH TO GITHUB ────────────────────────────────────────────────
  async function pushToGitHub(summaries) {
    log("Pushing summaries.json to GitHub...");
    const content = btoa(unescape(encodeURIComponent(JSON.stringify(summaries, null, 2))));
    const apiUrl = `https://api.github.com/repos/${GITHUB_REPO}/contents/summaries.json`;
    const headers = {
      Authorization: `token ${GITHUB_TOKEN}`,
      Accept: "application/vnd.github.v3+json",
      "Content-Type": "application/json"
    };

    // Get existing SHA if file exists
    let sha = null;
    try {
      const r = await fetch(`${apiUrl}?ref=${GITHUB_BRANCH}`, { headers });
      if (r.ok) sha = (await r.json()).sha;
    } catch {}

    const body = {
      message: `chore: weekly summaries ${formatDate(new Date())}`,
      content,
      branch: GITHUB_BRANCH,
      ...(sha ? { sha } : {})
    };

    const r = await fetch(apiUrl, { method: "PUT", headers, body: JSON.stringify(body) });
    if (!r.ok) throw new Error(`GitHub push failed: ${r.status} ${await r.text()}`);
    log("✅ Pushed to GitHub!");
  }

  // ── MAIN ──────────────────────────────────────────────────────────────────
  try {
    if (GITHUB_TOKEN === "YOUR_GITHUB_TOKEN_HERE") {
      throw new Error("Set GITHUB_TOKEN at the top of the script first!");
    }

    // Must be on the meetings list page with results loaded
    const meetings = scrapeMeetingsFromTable();
    if (meetings.length === 0) {
      log("No meetings found in table. Make sure you're on the search results page with meetings loaded.");
      return;
    }

    // Only process recent meetings (last 2 weeks)
    const twoWeeksAgo = new Date(Date.now() - 14 * 24 * 60 * 60 * 1000);
    const recentMeetings = meetings.filter(m => {
      const [d, mo, y] = m.date.split("/");
      return new Date(`${y}-${mo}-${d}`) >= twoWeeksAgo;
    });
    log(`Processing ${recentMeetings.length} recent meetings (last 2 weeks)`);

    const summaries = [];

    for (const meeting of recentMeetings) {
      const title = `${meeting.type} מס' ${meeting.id}`;
      log(`\n📋 Meeting: ${title} (${meeting.date})`);

      const entry = { id: meeting.id, title, date: meeting.date, docs: [] };

      const docs = await getDocumentsForMeeting(meeting);

      for (const doc of docs) {
        log(`  📄 Document: ${doc.label}`);
        const text = await extractTextFromDoc(doc);

        if (!text) {
          entry.docs.push({ label: doc.label, summary: "Could not extract PDF text." });
          continue;
        }

        log(`  Extracted ${text.length} chars`);
        const summary = await summarize(text, title, meeting.date);
        entry.docs.push({
          label: doc.label,
          summary: summary || "Summarization failed — check proxy is running."
        });
      }

      summaries.push(entry);

      // Go back to list page between meetings
      location.hash = "#search/GetMeetingByDate&siteid=16&v=0&fd=30/11/2025&td=30/06/2026&l=true&arguments=siteid,v,fd,td,l";
      await sleep(2000);
    }

    log(`\n✅ Done! ${summaries.length} meetings summarized`);
    console.log("Preview:", JSON.stringify(summaries, null, 2).slice(0, 800));

    await pushToGitHub(summaries);
    log("🎉 Complete! GitHub Actions will send the email on Friday.");

  } catch (err) {
    console.error("❌ Fatal error:", err);
  }

})();
