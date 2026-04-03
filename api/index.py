"""
StoryCause Donor Health Check™ — Vercel API
Stateless FastAPI. One request in, full JSON out.
"""
import sys, os, io, json
from typing import Optional

# Fix imports when running from repo root (local dev) vs api/ dir (Vercel)
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import pandas as pd
from fastapi import FastAPI, UploadFile, File, Form, HTTPException, Request
from fastapi.responses import PlainTextResponse
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.base import BaseHTTPMiddleware
from pydantic import BaseModel
import anthropic

from segmentation import build_donor_summary, segment_donors as run_seg
from analytics import (
    compute_all_metrics, compute_file_growth,
    compute_growth_dynamics, compute_ltv_projection,
    compute_large_gift_donors,
)

# ── App ───────────────────────────────────────────────────────────────────────

app = FastAPI(title="StoryCause DHC API", version="1.0.0")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])

ANTHROPIC_API_KEY = os.environ.get("ANTHROPIC_API_KEY", "")
DASHBOARD_PASSWORD = os.environ.get("DASHBOARD_PASSWORD", "")

# ── Optional password gate ────────────────────────────────────────────────────

class AuthMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        if not DASHBOARD_PASSWORD or not request.url.path.startswith("/api"):
            return await call_next(request)
        if request.url.path == "/api/health":
            return await call_next(request)
        if request.headers.get("X-Dashboard-Key") != DASHBOARD_PASSWORD:
            from fastapi.responses import JSONResponse
            return JSONResponse({"detail": "Unauthorized"}, status_code=401)
        return await call_next(request)

app.add_middleware(AuthMiddleware)

# ── Column normalisation ──────────────────────────────────────────────────────

REQUIRED = {
    "account_id":      ["account_id", "id", "constituent_id", "donor_id", "account number"],
    "donation_date":   ["donation_date", "gift_date", "date", "gift date", "transaction_date"],
    "donation_amount": ["donation_amount", "amount", "gift_amount", "gift amount", "revenue"],
}
OPTIONAL = {
    "account_type":      ["account_type", "type", "constituent_type"],
    "city":              ["city"],
    "zip_code":          ["zip_code", "zip", "postal_code"],
    "email":             ["email", "email_address", "primary_email"],
    "solicitation_code": ["solicitation_code", "appeal_code", "appeal"],
    "designation_code":  ["designation_code", "fund_code", "designation"],
    "transaction_type":  ["transaction_type", "payment_type"],
    "gift_type":         ["gift_type", "type_of_gift"],
}

def normalise(df: pd.DataFrame) -> tuple[pd.DataFrame, list[str]]:
    flags, rename, lower = [], {}, {c.lower().strip(): c for c in df.columns}
    for canon, aliases in {**REQUIRED, **OPTIONAL}.items():
        if canon in df.columns:
            continue
        match = next((lower[a] for a in aliases if a.lower() in lower), None)
        if match:
            rename[match] = canon
        elif canon in REQUIRED:
            flags.append(f"Required column '{canon}' not found.")
    return df.rename(columns=rename), flags

# ── Claude ────────────────────────────────────────────────────────────────────

async def claude(system: str, prompt: str, max_tokens: int = 2500) -> str:
    if not ANTHROPIC_API_KEY:
        return "Add ANTHROPIC_API_KEY in Vercel Environment Variables to enable AI features."
    try:
        client = anthropic.AsyncAnthropic(api_key=ANTHROPIC_API_KEY)
        msg = await client.messages.create(
            model="claude-sonnet-4-6", max_tokens=max_tokens,
            system=system, messages=[{"role": "user", "content": prompt}],
        )
        return msg.content[0].text
    except Exception as e:
        return f"AI error: {e}"

# ── Models ────────────────────────────────────────────────────────────────────

class RoadmapRequest(BaseModel):
    metrics: dict
    segment: str = "all"
    tone: str = "strategic"

class SOWRequest(BaseModel):
    prospect_name: str
    contact_name: Optional[str] = None
    ohp_completed: bool = True
    years_requested: int = 10

# ── Routes ────────────────────────────────────────────────────────────────────

@app.get("/api/health")
async def health():
    return {"status": "ok"}


@app.post("/api/analyze")
async def analyze(
    donor_file: UploadFile = File(...),
    client_name: str = Form(...),
    fiscal_year_end_month: int = Form(6),
    analysis_year: Optional[int] = Form(None),
    ohp_file: Optional[UploadFile] = File(None),
):
    # Read + parse donor CSV
    try:
        df = pd.read_csv(io.BytesIO(await donor_file.read()), low_memory=False)
    except Exception as e:
        raise HTTPException(400, f"Cannot read CSV: {e}")

    original = len(df)
    df, flags = normalise(df)
    missing = [c for c in REQUIRED if c not in df.columns]
    if missing:
        raise HTTPException(400, f"Missing required columns: {missing}")

    pre = len(df)
    df = df.dropna(subset=["account_id"])
    missing_ids = pre - len(df)

    df["donation_date"] = pd.to_datetime(df["donation_date"], errors="coerce")
    missing_dates = int(df["donation_date"].isna().sum())
    df = df.dropna(subset=["donation_date"])

    df["donation_amount"] = pd.to_numeric(
        df["donation_amount"].astype(str).str.replace(r"[$,]", "", regex=True), errors="coerce"
    )
    missing_amounts = int(df["donation_amount"].isna().sum())
    df = df[df["donation_amount"] > 0].dropna(subset=["donation_amount"])

    # Filter deceased / gone away / bad address (Data Guide field 8)
    deceased_removed = 0
    for col in ["deceased", "bad_address", "gone_away", "do_not_contact"]:
        if col in df.columns:
            mask = df[col].astype(str).str.upper().isin(["Y", "YES", "1", "TRUE"])
            deceased_removed += int(mask.sum())
            df = df[~mask]
    if deceased_removed > 0:
        flags.append(f"Removed {deceased_removed} records flagged as deceased/bad address/gone away.")

    fy = fiscal_year_end_month
    df["fiscal_year"] = df["donation_date"].apply(
        lambda d: d.year + 1 if (fy != 12 and d.month > fy) else d.year
    )

    fiscal_years = sorted(df["fiscal_year"].unique().tolist())
    if not fiscal_years:
        raise HTTPException(400, "No valid fiscal years found in data.")

    year = analysis_year or max(fiscal_years)
    final = len(df)
    flagged = original - final
    confidence = max(0, 100 - min(50, int(flagged / original * 100)) - len(flags) * 10)

    # Large Gift Donors ($10k+) — computed from raw df per DHC methodology
    # These are tracked SEPARATELY from the lifecycle analysis (DHC sample pages 4-6)
    large_gift = compute_large_gift_donors(df, analysis_year=year)

    # Optional OHP join
    ohp_info = None
    donor_summary = build_donor_summary(df, fiscal_year_end_month=fy)
    merged = donor_summary

    if ohp_file and ohp_file.filename:
        try:
            ohp = pd.read_csv(io.BytesIO(await ohp_file.read()), low_memory=False)
            lower = {c.lower().strip(): c for c in ohp.columns}
            id_col = next((lower[a] for a in ["account_id","donor_id","id","constituent_id"] if a in lower), None)
            if id_col:
                if id_col != "account_id":
                    ohp = ohp.rename(columns={id_col: "account_id"})
                ohp = ohp.dropna(subset=["account_id"]).set_index("account_id")
                matched = len(set(df["account_id"].astype(str)) & set(ohp.index.astype(str)))
                ohp_info = {"records": len(ohp), "matched": matched,
                            "coverage_pct": round(matched / max(len(donor_summary), 1) * 100, 1)}
                merged = donor_summary.join(ohp, how="left", rsuffix="_ohp")
        except Exception:
            pass  # OHP is optional

    # DHC pipeline
    segs    = run_seg(merged, analysis_year=year)
    metrics = compute_all_metrics(segs, year)
    fg      = compute_file_growth(segs, year)
    gd      = compute_growth_dynamics(segs, year)
    ltv     = compute_ltv_projection(segs, year)

    # Renewal (13-24) — surface as top-level KPI (it's in every DHC Summary table)
    renewal_13_24 = metrics.get("segments", {}).get(
        "lapsed_13_24", {}
    ).get("pct_donors_giving", None)

    return {
        "status": "complete",
        "client_name": client_name,
        "analysis_year": year,
        "metrics": metrics,
        "file_growth": fg,
        "growth_dynamics": gd,
        "ltv": ltv,
        "large_gift": large_gift,
        "summary_kpis": {
            "overall_retention_pct": metrics.get("totals", {}).get("overall_retention_pct"),
            "renewal_13_24_pct": renewal_13_24,
            "overall_frequency": metrics.get("totals", {}).get("gifts_per_active_donor"),
            "average_gift": metrics.get("totals", {}).get("average_gift"),
            "revenue_per_active": metrics.get("totals", {}).get("revenue_per_active"),
            "general_revenue": large_gift.get("general_revenue"),
            "large_gift_revenue": large_gift.get("revenue"),
            "total_revenue": large_gift.get("total_revenue"),
        },
        "data_rules": {
            "donor_exclusions": "Deceased, bad address, and gone away records removed"
                                if deceased_removed > 0 else "All donors included",
            "gift_exclusions": "Positive amounts only; $0 and negative gifts excluded",
            "fiscal_year_basis": f"{'Jul' if fy == 6 else 'Jan'}–{'Jun' if fy == 6 else 'Dec'}",
            "analysis_year": year,
            "data_through": f"FY{year} end",
        },
        "data_quality": {
            "records_parsed": final, "records_flagged": flagged,
            "unique_donors": int(df["account_id"].nunique()),
            "fiscal_years": fiscal_years, "confidence_score": confidence,
            "missing_dates": missing_dates, "missing_amounts": missing_amounts,
            "missing_account_ids": missing_ids, "flags": flags, "ohp": ohp_info,
        },
    }


@app.post("/api/roadmap")
async def roadmap(req: RoadmapRequest):
    tone_map = {
        "strategic":      "Data-driven. Reference specific metrics. Actionable.",
        "conversational": "Warm, relationship-focused. Emphasize story and connection.",
        "executive":      "Concise. One priority per segment. Board-ready.",
    }
    seg_filter = (
        f"Focus ONLY on the '{req.segment}' segment."
        if req.segment != "all" else "Cover all six lifecycle segments."
    )
    system = (
        "You are the StoryCause Donor Intelligence Engine. Expert in nonprofit fundraising, "
        "donor lifecycle management, and story-driven engagement. "
        "Ground every recommendation in the DHC metrics provided. Never fabricate data."
    )
    prompt = f"""
Generate a Donor Road Map from the FY{req.metrics.get('analysis_year','')} DHC results below.

{seg_filter}
Tone: {tone_map.get(req.tone, tone_map['strategic'])}

Metrics:
{json.dumps(req.metrics, indent=2)}

Per segment: (1) one-sentence health assessment  (2) biggest opportunity or risk
(3) 2–3 actionable recommendations citing the metrics  (4) StoryCause story engagement angle.
Format: clean Markdown, ## header per segment. End with overall strategic priorities.
"""
    text = await claude(system, prompt)
    return {"roadmap": text}


@app.post("/api/sow")
async def sow(req: SOWRequest):
    ohp = (f"{req.prospect_name} has completed the StoryCause Oral History Project."
           if req.ohp_completed else f"{req.prospect_name} is a prospective StoryCause partner.")
    system = (
        "Senior partnership director at StoryCause (PCI). "
        "Write professional, warm, benefit-forward Statements of Work. Plain English."
    )
    prompt = f"""Write a complete SOW for the StoryCause Donor Health Check™.

Client: {req.prospect_name}
{"Contact: " + req.contact_name if req.contact_name else ""}
OHP: {ohp}
Data requested: {req.years_requested} years

Sections: Background & Objectives · Requirements · Deliverables · What Makes This Different · Next Steps
Tone: Professional and warm. Partnership offer. Analysis is at no cost to the client.
Brand: StoryCause — "People who share stories, give."
Format: clean Markdown."""
    text = await claude(system, prompt, max_tokens=2000)
    return {"sow": text, "prospect": req.prospect_name}


@app.get("/api/report/download")
async def download(client_name: str = "Client", analysis_year: int = 2024):
    content = f"# StoryCause Donor Health Check™\n## {client_name} · FY{analysis_year}\n\n*Generated by StoryCause — \"People who share stories, give.\"*\n\nFor the full interactive report, view the dashboard at your deployment URL.\n"
    safe = "".join(c if c.isalnum() or c in " _-" else "_" for c in client_name)
    return PlainTextResponse(
        content,
        headers={"Content-Disposition": f'attachment; filename="DHC_{safe}_FY{analysis_year}.md"'},
        media_type="text/markdown",
    )
