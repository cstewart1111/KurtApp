"""
StoryCause DHC — Formatting Utilities
Renders DHC metrics and reports as JSON or Markdown.
"""
import json
from typing import Optional
from segmentation import SEGMENTS, SEGMENT_ORDER


CHARACTER_LIMIT = 100_000


def fmt_currency(value: float) -> str:
    """Format a float as a currency string."""
    if value >= 1_000_000:
        return f"${value/1_000_000:.2f}M"
    if value >= 1_000:
        return f"${value:,.0f}"
    return f"${value:.2f}"


def fmt_pct(value: float) -> str:
    return f"{value:.1f}%"


def truncate(text: str, limit: int = CHARACTER_LIMIT) -> str:
    if len(text) <= limit:
        return text
    return text[:limit] + "\n\n[Report truncated. Request individual sections for full details.]"


# ── Data Quality Report ───────────────────────────────────────────────────────

def format_data_quality(report: dict, fmt: str = "markdown") -> str:
    if fmt == "json":
        return json.dumps(report, indent=2)

    lines = [
        f"# 📋 Data Quality Report — {report.get('client_name', 'Client')}",
        "",
        "## Donor Giving History",
        f"- Records parsed: **{report['donor_file']['records_parsed']:,}**",
        f"- Records flagged: **{report['donor_file']['records_flagged']:,}**",
        f"- Missing donation dates: **{report['donor_file']['missing_dates']:,}**",
        f"- Missing amounts: **{report['donor_file']['missing_amounts']:,}**",
        f"- Missing account IDs: **{report['donor_file']['missing_account_ids']:,}**",
        f"- Unique donors: **{report['donor_file']['unique_donors']:,}**",
        f"- Unique fiscal years: **{', '.join(map(str, sorted(report['donor_file']['fiscal_years'])))}**",
        f"- Analysis year set to: **{report.get('analysis_year', 'N/A')}**",
        f"- Data confidence score: **{report['donor_file']['confidence_score']}/100**",
    ]

    if report.get("ohp_file"):
        ohp = report["ohp_file"]
        lines += [
            "",
            "## OHP Interview Data",
            f"- Records parsed: **{ohp['records_parsed']:,}**",
            f"- Unique donors with interviews: **{ohp['unique_donors']:,}**",
            f"- Donors matched to giving history: **{ohp.get('matched_donors', 'N/A'):,}**" if isinstance(ohp.get('matched_donors'), int) else f"- Donors matched to giving history: **{ohp.get('matched_donors', 'N/A')}**",
            f"- OHP coverage of giving file: **{ohp.get('coverage_pct', 'N/A')}%**",
        ]

    if report.get("flags"):
        lines += ["", "## ⚠️ Flags", ""]
        for flag in report["flags"]:
            lines.append(f"- {flag}")

    return "\n".join(lines)


# ── Segment Metrics ───────────────────────────────────────────────────────────

def format_segment_metrics(metrics: dict, fmt: str = "markdown") -> str:
    if fmt == "json":
        return json.dumps(metrics, indent=2)

    seg = metrics
    label = seg.get("segment_label", seg.get("segment", "Unknown"))
    lines = [
        f"## {label}",
        "",
        f"| Metric | Value |",
        f"|--------|-------|",
        f"| Available Donors | {seg.get('available', 0):,} |",
        f"| Active Donors | {seg.get('active', 0):,} |",
        f"| % Donors Giving | {fmt_pct(seg.get('pct_donors_giving', 0))} |",
        f"| Gifts | {seg.get('gifts', 0):,} |",
        f"| Gifts / Active Donor | {seg.get('gifts_per_active_donor', 0):.2f} |",
        f"| Revenue | {fmt_currency(seg.get('revenue', 0))} |",
        f"| Average Gift | {fmt_currency(seg.get('average_gift', 0))} |",
        f"| Revenue / Active Donor | {fmt_currency(seg.get('revenue_per_active', 0))} |",
        f"| Revenue / Available Donor | {fmt_currency(seg.get('revenue_per_available', 0))} |",
    ]

    if "conversion_pct" in seg:
        lines.append(f"| Conversion % (2+ gifts) | {fmt_pct(seg['conversion_pct'])} |")

    return "\n".join(lines)


def format_all_metrics(metrics: dict, fmt: str = "markdown") -> str:
    if fmt == "json":
        return json.dumps(metrics, indent=2)

    totals = metrics["totals"]
    year = metrics["analysis_year"]

    lines = [
        f"# 📊 Donor Health Check™ Metrics — FY{year}",
        "",
        "## Overall Summary",
        "",
        f"| Metric | Value |",
        f"|--------|-------|",
        f"| Active Donors | {totals['active_donors']:,} |",
        f"| Total Gifts | {totals['total_gifts']:,} |",
        f"| Total Revenue | {fmt_currency(totals['total_revenue'])} |",
        f"| Overall Retention | {fmt_pct(totals['overall_retention_pct'])} |",
        f"| Gifts / Active Donor | {totals['gifts_per_active_donor']:.2f} |",
        f"| Average Gift | {fmt_currency(totals['average_gift'])} |",
        f"| Revenue / Active Donor | {fmt_currency(totals['revenue_per_active'])} |",
        "",
        "---",
        "",
    ]

    for seg_key in SEGMENT_ORDER:
        if seg_key in metrics["segments"]:
            lines.append(format_segment_metrics(metrics["segments"][seg_key], "markdown"))
            lines.append("")

    return truncate("\n".join(lines))


# ── Growth Dynamics ───────────────────────────────────────────────────────────

def format_growth_dynamics(gd: dict, year: int, fmt: str = "markdown") -> str:
    if fmt == "json":
        return json.dumps(gd, indent=2)

    r = gd["retained_donors"]
    l = gd["lapsed_donors"]
    n = gd["new_donors_acquired"]
    re = gd["reactivated_donors"]

    net = gd["net_win_loss_revenue"]
    verdict = gd["win_vs_lapse"]
    verdict_emoji = "🟢" if verdict == "WIN" else "🔴"

    return "\n".join([
        f"# {verdict_emoji} Growth Dynamics — FY{year} ({verdict})",
        "",
        "## Retained Donors",
        f"| | Count | Revenue |",
        f"|--|-------|---------|",
        f"| Total Retained | {r['count']:,} | — |",
        f"| ↑ Upgraded | {r['upgraded_count']:,} | +{fmt_currency(r['upgraded_revenue_gain'])} |",
        f"| → Same | {r['same_count']:,} | +$0 |",
        f"| ↓ Downgraded | {r['downgraded_count']:,} | {fmt_currency(r['downgraded_revenue_loss'])} |",
        "",
        "## Lapsed Donors",
        f"- Donors lapsed: **{l['count']:,}**",
        f"- Revenue lost: **{fmt_currency(l['prior_year_revenue_lost'])}**",
        "",
        "## New & Reactivated",
        f"- New donors acquired: **{n['count']:,}** → {fmt_currency(n['revenue'])}",
        f"- Lapsed donors reactivated: **{re['count']:,}** → {fmt_currency(re['revenue'])}",
        "",
        "---",
        f"**Net Revenue Change: {'+' if net >= 0 else ''}{fmt_currency(net)}**",
    ])


# ── LTV Projection ────────────────────────────────────────────────────────────

def format_ltv(ltv: dict, fmt: str = "markdown") -> str:
    if fmt == "json":
        return json.dumps(ltv, indent=2)

    if "error" in ltv:
        return f"⚠️ LTV Error: {ltv['error']}"

    lines = [
        f"# 📈 Long-Term Value — Class of FY{ltv.get('analysis_year', '')}",
        "",
        f"- New Donors: **{ltv['new_donor_count']:,}**",
        f"- Year 1 Revenue: **{fmt_currency(ltv['first_year_revenue'])}**",
        f"- Revenue per Donor: **{fmt_currency(ltv['first_year_revenue_per_donor'])}**",
        f"- Cost of Acquisition: **{fmt_currency(ltv['cost_of_acquisition'])}**",
        f"- Year 1 ROI: **{ltv['first_year_roi']:.2f}x**",
        "",
        "## 5-Year Projection",
        "",
        "| Year | Rev/Donor | Cumulative Rev | LT ROI |",
        "|------|-----------|---------------|--------|",
    ]

    for p in ltv["projections"]:
        lines.append(
            f"| Year {p['year']} | {fmt_currency(p['revenue_per_donor'])} | "
            f"{fmt_currency(p['cumulative_revenue_per_donor'])} | {p['lt_roi']:.2f}x |"
        )

    lines += [
        "",
        f"**5-Year LTV: {fmt_currency(ltv['five_year_ltv'])} per donor**",
    ]
    return "\n".join(lines)


# ── Full Narrative Report Shell ───────────────────────────────────────────────

def format_narrative_shell(
    client_name: str,
    analysis_year: int,
    metrics: dict,
    growth_dynamics: dict,
    ltv: dict,
    file_growth: dict,
    roadmap_md: str = "",
) -> str:
    """
    Build the complete StoryCause DHC narrative report in Markdown.
    The AI-generated roadmap is appended if provided.
    """
    totals = metrics["totals"]

    header = f"""# StoryCause Donor Health Check™
## {client_name} · FY{analysis_year}

---

> *"People who share stories, give."*
> This report combines donor giving history with insights from the StoryCause
> Oral History Project to give {client_name} a complete picture of donor health,
> lifecycle patterns, and the path forward.*

---

## Executive Summary

| | Value |
|--|-------|
| Active Donors | {totals['active_donors']:,} |
| Total Gifts | {totals['total_gifts']:,} |
| Total Revenue | {fmt_currency(totals['total_revenue'])} |
| Overall Retention | {fmt_pct(totals['overall_retention_pct'])} |
| Average Gift | {fmt_currency(totals['average_gift'])} |
| Revenue per Active Donor | {fmt_currency(totals['revenue_per_active'])} |

---

## Donor File Overview

- Donors active last year: **{file_growth['donors_active_last_year']:,}**
- New donors acquired: **{file_growth['new_donors_acquired']:,}**
- Reactivated donors: **{file_growth['reactivated_donors']:,}**
- Retained donors: **{file_growth['retained_donors']:,}**
- **Donors active this year: {file_growth['donors_active_this_year']:,}**

---
"""

    metrics_section = format_all_metrics(metrics, "markdown")
    gd_section = format_growth_dynamics(growth_dynamics, analysis_year, "markdown")
    ltv_section = format_ltv(ltv, "markdown")

    roadmap_section = ""
    if roadmap_md:
        roadmap_section = f"\n\n---\n\n{roadmap_md}"

    full_report = header + "\n" + metrics_section + "\n\n---\n\n" + gd_section + "\n\n---\n\n" + ltv_section + roadmap_section

    return truncate(full_report)
