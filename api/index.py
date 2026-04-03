"""
StoryCause Donor Health Check™ — Vercel API
Stateless FastAPI. Every request is self-contained.
No session state — CSV processed in-flight, results returned as JSON.
The React frontend holds all state in useState.
"""
import io
import os
import json
from typing import Optional

import pandas as pd
from fastapi import FastAPI, UploadFile, File, Form, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.base import BaseHTTPMiddleware
from fastapi.responses import Response, PlainTextResponse
from pydantic import BaseModel
import anthropic

from segmentation import build_donor_summary, segment_donors as run_segmentation, SEGMENT_ORDER
from analytics import (
    compute_all_metrics,
    compute_file_growth,
    compute_growth_dynamics,
    compute_ltv_projection,
)

# ── App ───────────────────────────────────────────────────────────────────────

app = FastAPI(
    title="StoryCause DHC API",
    description="Stateless Donor Health Check analytics API",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

ANTHROPIC_API_KEY = os.environ.get("ANTHROPIC_API_KEY", "")
DASHBOARD_PASSWORD = os.environ.get("DASHBOARD_PASSWORD", "")

# ── Optional password middleware ──────────────────────────────────────────────

class DashboardAuthMiddleware(BaseHTTPMiddleware):
    SKIP_PATHS = {"/api/health"}

    async def dispatch(self, request: Request, call_next):
        if not DASHBOARD_PASSWORD:
            return await call_next(request)
        if not request.url.path.startswith("/api"):
            return await call_next(request)
        if request.url.path in self.SKIP_PATHS:
            return await call_next(request)
        key = request.headers.get("X-Dashboard-Key", "")
        if key != DASHBOARD_PASSWORD:
            return Response(
                content='{"detail":"Invalid or missing dashboard key."}',
                status_code=401,
                media_type="application/json",
            )
        return await call_next(request)

app.add_middleware(DashboardAuthMiddleware)

# ── Column normalisation ──────────────────────────────────────────────────────

REQUIRED_COLS = {
    "account_id":      ["account_id","id","constituent_id","donor_id","account number"],
    "donation_date":   ["donation_date","gift_date","date","gift date","transaction_date"],
    "donation_amount": ["donation_amount","amount","gift_amount","gift amount","revenue"],
}

OPTIONAL_COLS = {
    "account_type":     ["account_type","type","constituent_type"],
    "city":             ["city"],
    "zip_code":         ["zip_code","zip","postal_code"],
    "email":            ["email","email_address","primary_email"],
    "solicitation_code":["solicitation_code","appeal_code","appeal"],
    "designation_code": ["designation_code","fund_code","designation"],
    "transaction_type": ["transaction_type","payment_type"],
    "gift_type":        ["gift_type","type_of_gift"],
}


def normalize_columns(df: pd.DataFrame) -> tuple[pd.DataFrame, list[str]]:
    flags = []
    rename = {}
    lower = {c.lower().strip(): c for c in df.columns}
    for canonical, aliases in {**REQUIRED_COLS, **OPTIONAL_COLS}.items():
        if canonical in df.columns:
            continue
        for alias in aliases:
            if alias.lower() in lower:
                rename[lower[alias.lower()]] = canonical
                break
        else:
            if canonical in REQUIRED_COLS:
                flags.append(f"Required column '{canonical}' not found.")
    if rename:
        df = df.rename(columns=rename)
    return df, flags


def confidence_score(flagged: int, parsed: int, flags: list) -> int:
    if parsed == 0:
        return 0
    return max(0, 100 - min(50, int(flagged / parsed * 100)) - len(flags) * 10)


# ── Claude helper ─────────────────────────────────────────────────────────────

async def call_claude(system: str, prompt: str, max_tokens: int = 2500) -> str:
    if not ANTHROPIC_API_KEY:
        return (
            "Set the ANTHROPIC_API_KEY environment variable in Vercel project settings "
            "to enable AI-generated roadmap and SOW content."
        )
    try:
        client = anthropic.AsyncAnthropic(api_key=ANTHROPIC_API_KEY)
        msg = await client.messages.create(
            model="claude-sonnet-4-6",
            max_tokens=max_tokens,
            system=system,
            messages=[{"role": "user", "content": prompt}],
        )
        return msg.content[0].text
    except Exception as e:
        return f"AI generation error: {str(e)}"


# ── Pydantic models for request bodies ───────────────────────────────────────

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
    return {"status": "ok", "service": "StoryCause DHC API (Vercel)"}


@app.post("/api/analyze")
async def analyze(
    donor_file: UploadFile = File(...),
    client_name: str = Form(...),
    fiscal_year_end_month: int = Form(6),
    analysis_year: Optional[int] = Form(None),
    ohp_file: Optional[UploadFile] = File(None),
):
    """
    Core DHC pipeline — fully stateless.
    Accepts donor CSV (required) + OHP CSV (optional).
    Processes everything in-flight and returns complete metrics JSON.
    """
    # ── Read donor CSV ────────────────────────────────────────────────────────
    try:
        contents = await donor_file.read()
        df = pd.read_csv(io.BytesIO(contents), low_memory=False)
    except Exception as e:
        raise HTTPException(400, f"Could not read donor CSV: {str(e)}")

    original_count = len(df)
    df, flags = normalize_columns(df)

    missing = [c for c in REQUIRED_COLS if c not in df.columns]
    if missing:
        raise HTTPException(400, {"error": f"Required columns missing: {missing}", "flags": flags})

    # Clean
    before = len(df)
    df = df.dropna(subset=["account_id"])
    missing_ids = before - len(df)

    df["donation_date"] = pd.to_datetime(df["donation_date"], errors="coerce")
    missing_dates = int(df["donation_date"].isna().sum())
    df = df.dropna(subset=["donation_date"])

    df["donation_amount"] = pd.to_numeric(
        df["donation_amount"].astype(str).str.replace(r"[$,]", "", regex=True),
        errors="coerce",
    )
    missing_amounts = int(df["donation_amount"].isna().sum())
    df = df[df["donation_amount"] > 0].dropna(subset=["donation_amount"])

    fy_end = fiscal_year_end_month
    df["fiscal_year"] = df["donation_date"].apply(
        lambda d: d.year + 1 if (fy_end != 12 and d.month > fy_end) else d.year
    )

    fiscal_years = sorted(df["fiscal_year"].unique().tolist())
    unique_donors = int(df["account_id"].nunique())
    final_count = len(df)
    flagged = original_count - final_count
    analysis_yr = analysis_year or (max(fiscal_years) if fiscal_years else None)
    confidence = confidence_score(flagged, original_count, flags)

    if analysis_yr is None:
        raise HTTPException(400, "No valid fiscal years found in donation data.")

    # ── Read OHP CSV (optional) ───────────────────────────────────────────────
    ohp_df = None
    ohp_info = None
    if ohp_file and ohp_file.filename:
        try:
            ohp_bytes = await ohp_file.read()
            ohp_raw = pd.read_csv(io.BytesIO(ohp_bytes), low_memory=False)
            # Normalise donor ID column
            ohp_cols_lower = {c.lower().strip(): c for c in ohp_raw.columns}
            id_col = next(
                (ohp_cols_lower[a] for a in ["account_id","donor_id","id","constituent_id"]
                 if a in ohp_cols_lower),
                None
            )
            if id_col:
                if id_col != "account_id":
                    ohp_raw = ohp_raw.rename(columns={id_col: "account_id"})
                ohp_df = ohp_raw.dropna(subset=["account_id"]).set_index("account_id")
                donor_ids = set(df["account_id"].astype(str).unique())
                ohp_ids = set(ohp_df.index.astype(str).unique())
                matched = len(donor_ids & ohp_ids)
                ohp_info = {
                    "records_parsed": len(ohp_df),
                    "matched_donors": matched,
                    "coverage_pct": round(matched / max(len(donor_ids), 1) * 100, 1),
                }
        except Exception:
            pass  # OHP is optional — silently skip if unreadable

    # ── DHC Pipeline ──────────────────────────────────────────────────────────
    donor_summary = build_donor_summary(df, fiscal_year_end_month=fy_end)

    if ohp_df is not None:
        merged = donor_summary.join(ohp_df, how="left", rsuffix="_ohp")
    else:
        merged = donor_summary

    segments_df = run_segmentation(merged, analysis_year=analysis_yr)
    metrics     = compute_all_metrics(segments_df, analysis_yr)
    file_growth = compute_file_growth(segments_df, analysis_yr)
    growth_dyn  = compute_growth_dynamics(segments_df, analysis_yr)
    ltv         = compute_ltv_projection(segments_df, analysis_yr)

    return {
        "status": "complete",
        "client_name": client_name,
        "analysis_year": analysis_yr,
        "metrics": metrics,
        "file_growth": file_growth,
        "growth_dynamics": growth_dyn,
        "ltv": ltv,
        "data_quality": {
            "client_name": client_name,
            "analysis_year": analysis_yr,
            "donor_file": {
                "records_parsed": final_count,
                "records_flagged": flagged,
                "missing_dates": missing_dates,
                "missing_amounts": missing_amounts,
                "missing_account_ids": int(missing_ids),
                "unique_donors": unique_donors,
                "fiscal_years": fiscal_years,
                "confidence_score": confidence,
            },
            "ohp_file": ohp_info,
            "flags": flags,
        },
    }


@app.post("/api/roadmap")
async def generate_roadmap(request: RoadmapRequest):
    """
    Stateless roadmap generation.
    Metrics are passed in the request body — no server state required.
    """
    metrics_json = json.dumps(request.metrics, indent=2)
    client = request.metrics.get("analysis_year", "client")
    year = request.metrics.get("analysis_year", "")

    segment_filter = (
        f"Focus ONLY on the '{request.segment}' segment."
        if request.segment != "all"
        else "Cover all six lifecycle segments."
    )
    tone_map = {
        "strategic":      "Be data-driven and action-oriented. Reference specific metrics.",
        "conversational": "Use warm, relationship-focused language. Emphasize story and connection.",
        "executive":      "Be concise. One priority recommendation per segment. Board-ready.",
    }

    system = (
        "You are the StoryCause Donor Intelligence Engine — expert in nonprofit fundraising, "
        "donor lifecycle management, and story-driven engagement. "
        "Your recommendations are grounded in the DHC metric data and StoryCause's "
        "white-glove philosophy. Never fabricate data. Always cite the metrics."
    )
    prompt = f"""
Generate a Donor Road Map for FY{year} based on the Donor Health Check™ results below.

{segment_filter}
Tone: {tone_map.get(request.tone, tone_map['strategic'])}

DHC Metrics:
{metrics_json}

For each segment, provide:
1. One-sentence health assessment
2. Single biggest opportunity or risk
3. 2–3 specific, actionable recommendations citing the metrics
4. StoryCause engagement angle (how OHP story capture applies)

Format as clean Markdown with ## headers per segment. End with overall strategic priorities.
"""

    roadmap = await call_claude(system, prompt, max_tokens=2500)
    return {"roadmap": roadmap, "year": year}


@app.post("/api/sow")
async def generate_sow(request: SOWRequest):
    """Stateless SOW generation."""
    ohp_ctx = (
        f"{request.prospect_name} has completed the StoryCause Oral History Project."
        if request.ohp_completed
        else f"{request.prospect_name} is a prospective StoryCause partner."
    )
    system = (
        "You are a senior partnership director at StoryCause (Publishing Concepts / PCI). "
        "Write professional, warm, benefit-forward Statements of Work. Plain English. No jargon."
    )
    prompt = f"""
Write a complete Statement of Work for the StoryCause Donor Health Check™ program.

Client: {request.prospect_name}
{"Contact: " + request.contact_name if request.contact_name else ""}
OHP Status: {ohp_ctx}
Years of donor data requested: {request.years_requested}

Include:
1. Background and Objectives
2. Requirements (what the client provides)
3. Deliverables (DHC report, lifecycle analysis, OHP overlay, Donor Road Map)
4. What Makes This Different
5. Next Steps

Tone: Professional and warm. This is a partnership offer.
Brand: StoryCause — "People who share stories, give."
Note: PCI offers this analysis at no cost to the partner.
Format as clean Markdown.
"""
    sow = await call_claude(system, prompt, max_tokens=2000)
    return {"sow": sow, "prospect": request.prospect_name}


@app.get("/api/report/download")
async def download_report(
    client_name: str = "client",
    analysis_year: int = 2024,
):
    """
    Lightweight download endpoint — returns a template Markdown report.
    Full data is in the frontend; this produces a formatted shell.
    For a full report with data, the frontend should generate it client-side.
    """
    content = f"""# StoryCause Donor Health Check™
## {client_name} · FY{analysis_year}

*Generated by StoryCause — "People who share stories, give."*

---

This report was generated by the StoryCause DHC platform.
For the full interactive report including all metrics, lifecycle analysis,
and AI-generated road map, please view the dashboard at your deployment URL.

---

© StoryCause / Publishing Concepts Inc.
"""
    safe = "".join(c if c.isalnum() or c in " _-" else "_" for c in client_name)
    return PlainTextResponse(
        content=content,
        headers={"Content-Disposition": f'attachment; filename="StoryCause_DHC_{safe}_FY{analysis_year}.md"'},
        media_type="text/markdown",
    )
