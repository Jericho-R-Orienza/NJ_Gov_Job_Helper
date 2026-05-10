# NJ Government Job Agent — Project Notes

**Date:** 2026-05-10  
**Status:** Planning complete — ready to build once resume is provided

---

## Project Goal

Build a **local Python tool** that automatically scrapes all NJ government job postings, compares them against a personal resume using the Claude API, and outputs a filtered list of matching jobs directly to the terminal and a saved results file.

---

## Target Website

**URL:** https://www.nj.gov/csc/jobs/otherstate/

This is a directory of ~35 NJ state department links. Each department links to its own separate careers page with its own website structure and technology stack.

---

## Why Full Crawl (All 35 Departments)

The decision was made to scrape **all departments**, not just ones that seem relevant. Reasoning: analyst/professional roles can appear in any department (e.g., Agriculture posting an Analyst Trainee role). Missing a single opportunity in a tough job market is not worth the risk of pre-filtering by department.

---

## Site Complexity — Tiered Scraper Approach

Because each department runs its own website, a tiered scraping strategy is required:

| Tier | Technology | Approach |
|---|---|---|
| Tier 1 | Static HTML | `requests` + `BeautifulSoup` |
| Tier 2 | JavaScript-rendered (ATS portals) | `playwright` (headless browser) |
| Tier 3 | Blocked / login-walled | Flag in output — "check manually" |

No department is silently skipped. Tier 3 sites appear in the output with a manual check notice.

**Examples of department site types:**
- Treasury, Cannabis, Rate Counsel → `treasuryjobs.nj.gov` (shared portal)
- Health → `njservices.service-now.com` (ServiceNow ATS)
- Rowan University → `jobs.rowan.edu` (Taleo ATS)
- Environmental Protection → `nj.gov/dep/jobs/` (static HTML)

---

## Architecture — Local Tool (Not Hosted)

This is a **local Python CLI tool**. No server, no hosting, no cloud infrastructure. The user runs it manually on their own machine whenever they want an update.

### File Structure

```
nj_job_agent/
│
├── .env                  ← Anthropic API key (never shared)
├── .env.example          ← Safe template for sharing/onboarding
├── resume.txt            ← User's resume in plain text
│
├── run.py                ← Entry point — python run.py
├── scraper.py            ← Tiered crawler for all 35 departments
├── matcher.py            ← Claude API resume-vs-job comparison
├── output.py             ← Prints results to terminal + saves file
│
├── results/              ← Auto-created folder, timestamped run files
│                            e.g. results_2026-05-10_09-00.txt
├── requirements.txt      ← All Python dependencies
└── README.md             ← Setup instructions
```

### How It Works

1. `run.py` kicks off the process
2. `scraper.py` crawls all 35 department sites, collects job titles + descriptions + URLs
3. `matcher.py` sends each job description + the user's resume to Claude (Haiku model) and gets a match/no-match verdict
4. Only matched jobs are kept
5. `output.py` prints the results to the terminal and saves a timestamped `.txt` file in `/results`

---

## Output Format

**No email.** Output is local only:

- **Terminal print:** Job title, department, URL, and why it's a match
- **Saved file:** `results/results_YYYY-MM-DD_HH-MM.txt` — persists between sessions so morning results are still available at end of day

This approach saves tokens (no email generation step) and removes all SMTP/email configuration complexity.

---

## Claude API Usage

- **Model:** Claude Haiku 4.5 (cheapest, sufficient for comparison tasks)
- **Purpose:** Resume vs. job description matching only
- **Estimated cost per run:** ~$0.05–$0.20 depending on number of active listings
- **Estimated monthly cost (2 runs/day):** ~$3–$10/month
- **API key source:** `console.anthropic.com` — separate from Claude.ai Pro subscription

---

## Understanding the Three Claude Products

| Product | What It Is | Cost |
|---|---|---|
| **Claude.ai Pro** | Chat subscription (this conversation) | $20/month flat |
| **Anthropic API** | Powers the job agent's Claude calls | Pay-per-token (~cents/run) |
| **Claude Code** | AI coding assistant in terminal/VS Code | Included with Pro subscription |

These are **three separate things.** The Pro subscription does not cover API usage in custom scripts.

---

## Claude Code — Setup Notes

Claude Code is **not needed to build this project** — all code is generated in chat and copy-pasted. However, it is available for future use.

### Two Ways to Install Claude Code in VS Code

**Option 1 — VS Code Extension (recommended for beginners):**
1. Open VS Code
2. Click the Extensions icon (puzzle piece) or press `Ctrl+Shift+X`
3. Search **"Claude Code"**
4. Install the one published by **Anthropic** (verified publisher)
5. A Spark icon appears in the sidebar — click to open

**Option 2 — npm CLI:**
```bash
npm install -g @anthropic-ai/claude-code
```
- Requires Node.js 18 or later
- Do **NOT** use `sudo` with this command
- After install, run `claude` in terminal to authenticate via browser

**Requirements:**
- Claude Pro, Max, Team, or Enterprise subscription (or API key)
- Free plan does not include Claude Code access
- Since the user has Pro — Claude Code is already included at no extra cost

---

## How to Run the Job Agent (Once Built)

```bash
# One-time setup
cd nj_job_agent
pip install -r requirements.txt

# Add your API key to .env
# Add your resume text to resume.txt

# Run anytime you want a job search update
python run.py
```

Results print to terminal and save automatically to `/results`.

---

## What's Still Needed to Build

- [ ] **User's resume** — paste as text or upload file in chat
- [ ] Code generation (all files listed above)

---

## Key Decisions Log

| Decision | Choice | Reason |
|---|---|---|
| Scope | All 35 departments | Can't afford to miss niche postings |
| Output method | Terminal + local file | Simpler, no email config, saves tokens |
| Hosting | Local machine only | Privacy, no server costs, user control |
| Scheduling | Manual runs | User preference — 1-2x/day on demand |
| Claude model | Haiku 4.5 | Cheapest model sufficient for matching |
| Email | Removed | Not needed for local tool |
