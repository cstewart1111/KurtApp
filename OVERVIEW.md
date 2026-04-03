# StoryCause Donor Health Check™ — App Overview

## What It Does

The StoryCause Donor Health Check™ (DHC) is an internal analytics platform that
turns a nonprofit's donor giving history into a lifecycle-based health report —
showing exactly where donors are in their relationship with the organization,
what they're worth, and what to do next.

It combines two unique data sources that no other vendor has together:

1. **Donor giving history** — 10 years of gift transactions from the organization's CRM
2. **OHP interview data** — First-person donor stories and sentiment captured through
   StoryCause's Oral History Project

The output is a complete Donor Health Check™ report with lifecycle segmentation,
retention metrics, growth dynamics, long-term value projections, and AI-generated
engagement recommendations tailored to each donor segment.

---

## The DHC Methodology

Every donor in the file is classified into one of six lifecycle stages based on
their giving pattern relative to the analysis year (Y):

| Segment | Definition | Why It Matters |
|---|---|---|
| **New Donors** | First gift ever in Y | Highest upgrade potential; 90-day window is critical |
| **2nd Year from New** | Acquired in Y-1, now in year 2 | Make-or-break retention moment |
| **Multi-Year Donors** | Consecutive giving in Y-1 AND Y-2 | Core revenue base; upgrade candidates |
| **2nd Year Regained** | Lapsed before Y-1, reactivated in Y-1 | High gift size on return; retain now |
| **Lapsed (13–24 Months)** | Gave in Y-2 but not Y-1 | Reactivation window still open |
| **Multi-Year Lapsed (25+)** | Last gift in Y-3 or earlier | Long-shot reactivation; story-led outreach |

For each segment, the platform calculates:
- Available donors (pool entering the year) and active donors (those who gave)
- Retention rate (% of available who gave)
- Revenue, average gift, gifts per donor
- Revenue per active and per available donor
- Conversion rate (for new donors: those who gave 2+ times)

---

## How It Works — The Pipeline

```
User uploads donor CSV
        ↓
[FastAPI] Normalize columns → validate required fields → clean bad rows
        ↓
[pandas] Build donor summary — aggregate gifts by fiscal year per donor
        ↓
[segmentation.py] Classify every donor into one of 6 lifecycle segments
        ↓
[analytics.py] Compute all DHC metrics per segment
              + Growth Dynamics (win vs. lapse, upgrade vs. downgrade)
              + 5-Year LTV projection for new donor cohort
              + File growth (new, retained, reactivated, lapsed counts)
        ↓
[FastAPI] Return complete JSON to the React frontend
        ↓
[React] Dashboard renders: Overview → Lifecycle → Growth → Road Map → SOW
```

**Key design decision:** The entire pipeline runs in a single HTTP request.
No database. No session. The server processes the CSV, computes everything,
and returns the full result as one JSON blob. The browser holds all state.

---

## The AI Layer

Two features use Anthropic's Claude API:

**Donor Road Map** — Claude receives the full DHC metrics JSON and generates
segment-specific engagement recommendations. Three tones available:
- *Strategic* — data-driven, cites specific metrics
- *Conversational* — warm, story-led, relationship-focused
- *Executive* — board-ready, one priority per segment

**SOW Generator** — Claude generates a tailored Statement of Work for a prospect
institution, referencing their OHP status and years of data requested.

Both features degrade gracefully — if `ANTHROPIC_API_KEY` is not set, the app
still runs fully and shows a clear message prompting the key to be added.

---

## The OHP Layer

If an OHP (Oral History Project) CSV is uploaded alongside the donor file,
the platform joins the two datasets on account ID. This adds:

- Interview coverage per segment (how many donors in each lifecycle stage
  have been interviewed)
- Sentiment score distribution (if a sentiment column is present)
- Planned giving signals (if a planned giving indicator column is present)

The OHP layer is optional. The app runs fully without it.

---

## What Gets Delivered

| Output | Format | Who It's For |
|---|---|---|
| Health Summary dashboard | Interactive web UI | Internal PCI team |
| Lifecycle Explorer | Interactive — click any segment | Internal analysis |
| Growth Dynamics chart | Win vs. Lapse visual | Internal review |
| Donor Road Map | AI Markdown narrative | Client-facing |
| Full DHC Report | Downloadable `.md` | Client-facing |
| Statement of Work | AI Markdown document | Prospect institutions |

---

## Tech Stack (Summary)

| Layer | Technology |
|---|---|
| Frontend | React 18 + Vite (JSX, single-file component) |
| Styling | Custom CSS — StoryCause brand system (teal/amber/cream, Cormorant + DM Sans) |
| Backend | Python FastAPI — stateless, Vercel serverless |
| Analytics | pandas + numpy — in-memory DHC pipeline |
| AI | Anthropic `claude-sonnet-4-6` — roadmap + SOW generation |
| Deployment | Vercel — Python API + static React build |
| MCP Server | FastMCP (Python) — 11 tools for Claude.ai integration |

---

## How to Use It

1. **Upload** your donor giving history CSV (one row per gift, 17-field spec)
2. Optionally upload your OHP interview data CSV
3. Hit **Upload & Analyze** — analysis runs in ~3 seconds for a 250-donor file
4. Browse the dashboard tabs: Overview, Lifecycle, Growth, Road Map, SOW
5. Generate the AI Road Map with your preferred tone
6. Download the full report or generate a SOW for a new prospect

**For demos:** Use `sample_data/sample_donors.csv` — 1,379 gifts across
250 donors spanning FY2017–FY2021. Covers all six lifecycle segments.

---

## Deployment

**Live:** Deployed on Vercel — auto-deploys on push to `main` branch of
`github.com/cstewart1111/KurtApp`.

**Environment variables required in Vercel:**
- `ANTHROPIC_API_KEY` — enables AI roadmap and SOW generation
- `DASHBOARD_PASSWORD` — optional password gate (recommended for client-facing use)

**Local dev:**
```bash
# Terminal 1 — Python API
cd api && uvicorn index:app --host 0.0.0.0 --port 8000

# Terminal 2 — React frontend
npm install && npm run dev
# Opens on localhost:5173, proxies /api/* to port 8000
```
