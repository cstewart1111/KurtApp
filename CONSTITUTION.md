---
name: project-constitution
description: >
  Enforces the technical standards, architecture decisions, and coding
  conventions for the StoryCause Donor Health Check™ platform. Trigger
  whenever writing, reviewing, or modifying any code, component, endpoint,
  or config in this project. This is the single source of truth.
---

# StoryCause DHC — Project Constitution

All code written for this project must comply with these standards.
No exceptions without an explicit Constitutional Amendment from the Product Owner (Colin Stewart / PCI).

---

## 1. Approved Tech Stack

| Layer | Technology | Notes |
|---|---|---|
| Frontend framework | **React 18 + Vite 5** | JSX, not TypeScript. No Next.js. |
| Styling | **Custom CSS + CSS variables** | StoryCause brand system in `src/index.css`. No Tailwind. |
| Backend | **Python FastAPI** | Stateless, serverless-compatible. No Django, Flask, or Express. |
| Analytics | **pandas + numpy** | In-memory DHC pipeline. No database in v1. |
| AI generation | **Anthropic Claude API** | Model: `claude-sonnet-4-6`. Used for roadmap + SOW only. |
| MCP server | **FastMCP (Python)** | 11 tools, separate from web app (`server.py`). |
| Deployment | **Vercel** | Python serverless (`api/`) + Vite static build (`dist/`). |
| Version control | **GitHub** | Repo: `github.com/cstewart1111/KurtApp` |
| Language (backend) | **Python 3.12** | Type hints where practical. Pydantic v2 for validation. |
| Language (frontend) | **JavaScript / JSX** | No TypeScript. |

Do not introduce any library, framework, or service outside this stack
without flagging it as a proposed Constitutional Amendment.

---

## 2. Repository Structure

```
/                           ← repo root (GitHub: KurtApp)
├── vercel.json             ← Vercel builds config (@vercel/python + @vercel/static-build)
├── requirements.txt        ← Python deps (pinned for Vercel lambda budget)
├── package.json            ← React/Vite build
├── vite.config.js          ← dev proxy to localhost:8000; build → dist/
├── index.html              ← Vite entry point
├── src/
│   ├── main.jsx            ← ReactDOM.createRoot
│   ├── App.jsx             ← Full dashboard (all components in one file, v1)
│   └── index.css           ← StoryCause brand design system (CSS variables)
├── api/
│   ├── index.py            ← Stateless FastAPI app (ONLY entry point Vercel invokes)
│   ├── segmentation.py     ← PCI lifecycle segmentation engine
│   ├── analytics.py        ← Metrics, LTV, growth dynamics, OHP sentiment
│   └── formatting.py       ← JSON/Markdown report renderers
├── sample_data/
│   └── sample_donors.csv   ← 250 donors, 5 years, all 17 StoryCause spec fields
├── .env.example            ← Required env vars (never commit actual values)
└── .gitignore              ← Excludes .env, *.csv, dist/, __pycache__/
```

MCP server lives separately in `storycause-dhc-final/` (not deployed to Vercel):
```
storycause-dhc-final/
├── server.py               ← FastMCP — 11 tools for the full DHC pipeline
├── state.py                ← Single-client session singleton (v1)
├── models.py               ← All Pydantic input models
└── api.py                  ← FastAPI web server (Replit deployment)
```

---

## 3. Architecture: Stateless API

**The golden rule: the server holds no state between requests.**

- `api/index.py` processes each request end-to-end and returns complete JSON
- The React frontend holds all session data in `useState` + `sessionStorage`
- No database, no Redis, no server-side sessions
- Each API call is fully self-contained

### Data flow
```
User uploads CSV
  → POST /api/analyze (multipart: donor_file, client_name, fiscal_year_end_month)
  → FastAPI reads CSV in-memory (pandas)
  → normalise → build_donor_summary → segment → compute_metrics → LTV → growth_dynamics
  → Returns complete JSON blob
  → React stores in useState, sessionStorage tracks client_name + analysis_year

User generates roadmap
  → POST /api/roadmap (JSON body: { metrics, segment, tone })
  → FastAPI calls Anthropic API with metrics embedded in prompt
  → Returns { roadmap: "markdown string" }

User generates SOW
  → POST /api/sow (JSON body: { prospect_name, ohp_completed, years_requested, ... })
  → FastAPI calls Anthropic API
  → Returns { sow: "markdown string" }
```

---

## 4. Python Standards

### File organisation
- `api/index.py` is the only file Vercel invokes — all routes live here
- Shared modules (`segmentation.py`, `analytics.py`, `formatting.py`) live in `api/`
- Always include at the top of `api/index.py`:
  ```python
  import sys, os
  sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
  ```
  This ensures sibling module imports work when uvicorn runs from the repo root.

### Imports
```python
# Correct middleware import (FastAPI 0.100+)
from starlette.middleware.base import BaseHTTPMiddleware
# NOT: from fastapi.middleware.base import BaseHTTPMiddleware
```

### Async
- All route handlers are `async def`
- All file reads use `await file.read()`
- Anthropic client uses `AsyncAnthropic`

### Pydantic models
- Use Pydantic v2 for all request body models
- Required for JSON body endpoints (`roadmap`, `sow`)
- File upload endpoints use `Form()` + `File()` — not Pydantic models

### Error handling
- Always return actionable HTTP errors: `raise HTTPException(400, "descriptive message")`
- Wrap CSV reads and Anthropic calls in try/except
- OHP file is always optional — silently skip if unreadable, never crash

### Naming
- Functions: `snake_case`
- Constants: `SCREAMING_SNAKE_CASE`
- No `any` type equivalents — use explicit types and docstrings

---

## 5. Frontend Standards

### Component structure
- v1: all components in `src/App.jsx` (single file, no separate component files)
- v2+: extract to `src/components/` as `PascalCase.jsx`
- Default export for page-level components, named exports for utilities

### API calls
Always use the `apiCall` helper — never raw `fetch` for API routes:
```js
// Defined at top of App.jsx
const apiCall = (url, opts = {}) => {
  const key = sessionStorage.getItem('dhc_key') || ''
  return fetch(url, {
    ...opts,
    headers: { ...(opts.headers || {}), 'X-Dashboard-Key': key },
  })
}
```

### Request body conventions
| Endpoint | How to send data |
|---|---|
| `/api/analyze` | `FormData` (multipart — file upload) |
| `/api/roadmap` | JSON body with `Content-Type: application/json` |
| `/api/sow` | JSON body with `Content-Type: application/json` |
| `/api/report/download` | Query params (`?client_name=...&analysis_year=...`) |

### State management
- Analysis result: `useState` in `App` component
- Client name + year for download: `sessionStorage` key `dhc_analysis`
- Auth key: `sessionStorage` key `dhc_key`
- No Redux, Zustand, or Context API in v1

### Naming
- Components: `PascalCase` (`DashboardScreen`, `UploadScreen`, `SOWPanel`)
- Functions/variables: `camelCase` (`handleComplete`, `analysisData`, `activeTab`)
- CSS classes: `kebab-case` in `index.css`

---

## 6. StoryCause Brand Design System

All UI must follow the brand tokens defined in `src/index.css`.

### Colour palette
| Token | Hex | Usage |
|---|---|---|
| `--teal-800` | `#1B4F5A` | Primary — nav, CTAs, segment colours |
| `--teal-600` | `#2e7589` | Secondary teal |
| `--amber-500` | `#E8924A` | Accent — alerts, highlights, CTA hover |
| `--cream` | `#F7F3EE` | Page background |
| `--cream-dark` | `#ede7dd` | Card borders, dividers |
| `--slate-700` | `#2C3A47` | Body text |
| `--stone-400` | `#9e9589` | Muted labels |

### Typography
- Display / headings: `Cormorant Garamond` (serif, weights 300/400/600)
- Body / UI: `DM Sans` (sans-serif, weights 300/400/500/600)
- Load both from Google Fonts in `index.html`

### Card pattern
```css
background: white;
border-radius: var(--radius-lg);   /* 20px */
border: 1px solid var(--cream-dark);
box-shadow: var(--shadow-sm);
padding: 1.75rem;
```

### Never
- Use inline hex colours — always use CSS variables
- Override the brand fonts
- Add gradient backgrounds (flat surfaces only)
- Use a UI component library (Shadcn, MUI, Ant Design, etc.)

---

## 7. DHC Lifecycle Segments

PCI-owned logic. These definitions are canonical and must not be changed without a Constitutional Amendment.

| Segment key | Label | Definition |
|---|---|---|
| `new_donors` | New Donors | First gift ever in the analysis year |
| `second_year_from_new` | 2nd Year from New | Acquired in Y-1, now in year 2 |
| `multi_year` | Multi-Year Donors | Consecutive giving in Y-1 AND Y-2 |
| `second_year_regained` | 2nd Year Regained | Lapsed before Y-1, reactivated in Y-1 |
| `lapsed_13_24` | Lapsed (13–24 Months) | Gave in Y-2 but not Y-1 |
| `multi_year_lapsed_25plus` | Multi-Year Lapsed (25+) | Last gift in Y-3 or earlier |

Segmentation runs in `api/segmentation.py` → `segment_donors()`.
Metrics computed in `api/analytics.py` → `compute_all_metrics()`.

---

## 8. Environment Variables

| Variable | Required | Where set | Purpose |
|---|---|---|---|
| `ANTHROPIC_API_KEY` | Yes (for AI) | Vercel Env Vars / Replit Secrets | Roadmap + SOW generation |
| `DASHBOARD_PASSWORD` | No | Vercel Env Vars / Replit Secrets | Optional password gate on all `/api/*` |

Never commit actual values. Never log or expose keys in responses.

---

## 9. Vercel Deployment Config

`vercel.json` must always use the `builds` format — not `functions` with a `runtime` key.

```json
{
  "version": 2,
  "builds": [
    { "src": "api/index.py", "use": "@vercel/python" },
    { "src": "package.json", "use": "@vercel/static-build", "config": { "distDir": "dist" } }
  ],
  "routes": [
    { "src": "/api/(.*)", "dest": "api/index.py" },
    { "handle": "filesystem" },
    { "src": "/(.*)", "dest": "/index.html" }
  ]
}
```

Do not use `"runtime": "python3.12"` in the `functions` key — this is invalid and causes deploy failures.

---

## 10. Pre-Submit Checklist

Before presenting any code:

- [ ] `sys.path.insert` present at top of `api/index.py`
- [ ] Middleware imported from `starlette.middleware.base`, not `fastapi.middleware.base`
- [ ] All route handlers are `async def`
- [ ] JSON body endpoints use Pydantic models; file uploads use `Form()` + `File()`
- [ ] Frontend API calls use `apiCall()` helper, not raw `fetch()`
- [ ] SOW and roadmap use JSON body — not query params or FormData
- [ ] Brand tokens used — no hardcoded hex colours
- [ ] `vercel.json` uses `builds` format
- [ ] No `.csv` files committed (only `sample_data/sample_donors.csv`)
- [ ] No API keys hardcoded anywhere

---

## 11. Roadmap (v1.1+)

Features planned but out of scope for v1:

- Multi-client support (client switcher, namespaced analysis results)
- Persistent storage (Supabase or Vercel KV for session persistence across restarts)
- PDF export of narrative report
- donorCentrics benchmark comparisons
- OHP sentiment deep-dive by theme (NLP classification)

Any v1.1 work must be flagged as a Constitutional Amendment before implementation.

---

*Owned by Colin Stewart, VP of Partnerships, Publishing Concepts / StoryCause.*
*Any deviation from this constitution requires explicit approval.*
