// Haifa Committee Weekly Summary
// Run this in Claude in Chrome every Friday morning
// It fetches PDFs, summarizes them, and pushes to GitHub

const GITHUB_REPO = "eladlevy78/haifa-permits";
const GITHUB_TOKEN = ""; // Set via environment - fetched from page
const DAYS_BACK = 7;
const COMPLOT_BASE = "https://haifa.complot.co.il";
const SITE_ID = "16";

async function run() {
  console.log("=== Haifa Weekly Summary ===");
  
  // Step 1: Get GitHub token from page storage
  const token = window._githubToken || prompt("Enter your GitHub PAT_TOKEN:");
  if (!token) { console.error("No token provided"); return; }

  // Step 2: Fetch meetings from Complot
  const today = new Date();
  const weekAgo = new Date(today - 7 * 24 * 60 * 60 * 1000);
  const fd = weekAgo.toLocaleDateString("he-IL").replace(/\./g, "/");
  const td = today.toLocaleDateString("he-IL").replace(/\./g, "/");
  
  console.log(`Fetching meetings from ${fd} to ${td}...`);
  
  // Navigate to meetings page and get the list
  const meetingsUrl = `${COMPLOT_BASE}/yeshivot/#search/GetMeetingByDate&siteid=${SITE_ID}&v=0&fd=${fd}&td=${td}&l=true&arguments=siteid,v,fd,td,l`;
  
  // Step 3: Get meetings from DOM (we're already on the site)
  const rows = document.querySelectorAll("tr");
  const meetings = [];
  rows.forEach(row => {
    const cells = Array.from(row.querySelectorAll("td"));
    const link = row.querySelector("a[href*='getMeeting']");
    if (!link || cells.length < 3) return;
    const match = link.href.match(/getMeeting\((\d+),(\d+)\)/);
    if (!match) return;
    meetings.push({
      committeeId: match[1],
      meetingId: match[2],
      committee: cells[1]?.innerText.trim(),
      date: cells[2]?.innerText.trim(),
    });
  });
  
  console.log(`Found ${meetings.length} meetings`);
  
  // Step 4: For each meeting, get PDFs and summarize
  const summaries = [];
  
  for (const m of meetings) {
    console.log(`Processing meeting ${m.meetingId} - ${m.committee}...`);
    
    // Navigate to meeting page
    getMeeting(parseInt(m.committeeId), parseInt(m.meetingId));
    await new Promise(r => setTimeout(r, 2000));
    
    // Get PDF links
    const pdfs = Array.from(document.querySelectorAll("a[href*='.pdf']"))
      .map(a => ({ text: a.innerText.trim().replace(/\n.*/,""), href: a.href }));
    
    console.log(`  Found ${pdfs.length} PDFs`);
    
    const docs = [];
    for (const pdf of pdfs) {
      const isProtocol = pdf.text.includes("פרוטוקול") || pdf.text.includes("Protocol");
      
      // Download and summarize protocol PDFs
      let summary = "";
      if (isProtocol) {
        try {
          console.log(`  Summarizing: ${pdf.text}`);
          const pdfResp = await fetch(pdf.href);
          const blob = await pdfResp.blob();
          const b64 = await new Promise(res => {
            const r = new FileReader();
            r.onload = () => res(r.result.split(",")[1]);
            r.readAsDataURL(blob);
          });
          
          const claudeResp = await fetch("https://api.anthropic.com/v1/messages", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({
              model: "claude-sonnet-4-20250514",
              max_tokens: 1000,
              messages: [{
                role: "user",
                content: [
                  { type: "document", source: { type: "base64", media_type: "application/pdf", data: b64 }},
                  { type: "text", text: `Summarize in English the main decisions from this committee meeting protocol (${m.committee}, ${m.date}). 
                  For each decision include:
                  - The address/location if mentioned
                  - What was decided (approved/rejected/postponed)
                  - Brief reason
                  Format as bullet points. Maximum 10 bullets.` }
                ]
              }]
            })
          });
          
          if (claudeResp.ok) {
            const data = await claudeResp.json();
            summary = data.content?.[0]?.text || "";
            console.log(`  Summarized: ${summary.substring(0, 100)}...`);
          }
        } catch (e) {
          console.error(`  Error summarizing: ${e.message}`);
        }
      }
      
      docs.push({ text: pdf.text, href: pdf.href, isProtocol, summary });
      await new Promise(r => setTimeout(r, 500));
    }
    
    summaries.push({ ...m, docs });
  }
  
  // Step 5: Push summaries to GitHub
  console.log("Pushing summaries to GitHub...");
  
  const content = JSON.stringify({ 
    generated: new Date().toISOString(),
    period: { from: fd, to: td },
    meetings: summaries 
  }, null, 2);
  
  const b64Content = btoa(unescape(encodeURIComponent(content)));
  
  // Get current file SHA (if exists)
  let sha = "";
  try {
    const getResp = await fetch(`https://api.github.com/repos/${GITHUB_REPO}/contents/summaries.json`, {
      headers: { "Authorization": `Bearer ${token}`, "Accept": "application/vnd.github.v3+json" }
    });
    if (getResp.ok) {
      const data = await getResp.json();
      sha = data.sha;
    }
  } catch(e) {}
  
  const body = {
    message: `Weekly summary ${new Date().toLocaleDateString()}`,
    content: b64Content,
  };
  if (sha) body.sha = sha;
  
  const pushResp = await fetch(`https://api.github.com/repos/${GITHUB_REPO}/contents/summaries.json`, {
    method: "PUT",
    headers: {
      "Authorization": `Bearer ${token}`,
      "Content-Type": "application/json",
      "Accept": "application/vnd.github.v3+json"
    },
    body: JSON.stringify(body)
  });
  
  if (pushResp.ok) {
    console.log("✅ Summaries pushed to GitHub successfully!");
    console.log("GitHub Actions will now build and send the email.");
  } else {
    const err = await pushResp.json();
    console.error("❌ GitHub push failed:", err.message);
  }
  
  return summaries;
}

run();
