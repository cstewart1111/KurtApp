"""
StoryCause DHC — Analytics & Metrics Engine

Computes all v1 DHC metrics per lifecycle segment:
  - Available / Active donor counts
  - Retention rate (% donors giving)
  - Revenue and average gift
  - Gifts per active donor
  - Revenue per active / per available
  - Donor file growth (new, retained, reactivated, lapsed)
  - Growth Dynamics (win vs. lapse analysis)
  - Long-Term Value (LTV) projection for new donors
  - OHP sentiment overlay per segment
"""
import pandas as pd
import numpy as np
from typing import Optional
from segmentation import SEGMENTS, SEGMENT_ORDER, get_new_donor_conversion


# ── Per-Segment Metrics ───────────────────────────────────────────────────────

def compute_segment_metrics(
    segments_df: pd.DataFrame,
    segment_key: str,
    analysis_year: int,
) -> dict:
    """
    Compute all DHC metrics for a single lifecycle segment.

    For 'new_donors', 'available' == all acquired (active by definition).
    For all other segments, 'available' = pool entering analysis year,
    'active' = those who gave in analysis year.
    """
    seg = segments_df[segments_df["segment"] == segment_key]

    if segment_key == "new_donors":
        # New donors: all are 'available' and 'active' (first gift IS the qualifying gift)
        available = len(seg)
        active = available  # All new donors gave in Y by definition
        gifts = int(seg["analysis_year_gifts"].sum())
        revenue = float(seg["analysis_year_revenue"].sum())
        conversion = get_new_donor_conversion(segments_df, "account_id", analysis_year)

        gifts_per_donor = round(gifts / active, 2) if active else 0
        avg_gift = round(revenue / gifts, 2) if gifts else 0
        revenue_per_active = round(revenue / active, 2) if active else 0
        revenue_per_available = revenue_per_active  # same for new donors

        return {
            "segment": segment_key,
            "segment_label": SEGMENTS[segment_key],
            "available": available,
            "active": active,
            "pct_donors_giving": 100.0,
            "gifts": gifts,
            "gifts_per_active_donor": gifts_per_donor,
            "revenue": round(revenue, 2),
            "average_gift": avg_gift,
            "revenue_per_active": revenue_per_active,
            "revenue_per_available": revenue_per_available,
            "conversion_pct": conversion["conversion_pct"],
            "converted_donors": conversion["converted"],
        }

    else:
        available = len(seg)
        active_mask = seg["is_active"]
        active_donors = seg[active_mask]
        active = len(active_donors)

        gifts = int(active_donors["analysis_year_gifts"].sum())
        revenue = float(active_donors["analysis_year_revenue"].sum())

        pct_giving = round(active / available * 100, 1) if available else 0
        gifts_per_donor = round(gifts / active, 2) if active else 0
        avg_gift = round(revenue / gifts, 2) if gifts else 0
        revenue_per_active = round(revenue / active, 2) if active else 0
        revenue_per_available = round(revenue / available, 2) if available else 0

        return {
            "segment": segment_key,
            "segment_label": SEGMENTS[segment_key],
            "available": available,
            "active": active,
            "pct_donors_giving": pct_giving,
            "gifts": gifts,
            "gifts_per_active_donor": gifts_per_donor,
            "revenue": round(revenue, 2),
            "average_gift": avg_gift,
            "revenue_per_active": revenue_per_active,
            "revenue_per_available": revenue_per_available,
        }


def compute_all_metrics(
    segments_df: pd.DataFrame,
    analysis_year: int,
) -> dict:
    """
    Compute DHC metrics for all six lifecycle segments plus overall totals.
    """
    segment_metrics = {}
    for seg_key in SEGMENT_ORDER:
        segment_metrics[seg_key] = compute_segment_metrics(
            segments_df, seg_key, analysis_year
        )

    # Overall totals
    all_active = segments_df[segments_df["is_active"]]
    total_available = len(segments_df[segments_df["segment"] != "unclassified"])
    total_active = len(all_active)
    total_gifts = int(all_active["analysis_year_gifts"].sum())
    total_revenue = float(all_active["analysis_year_revenue"].sum())

    overall_retention = round(
        len(segments_df[
            (segments_df["is_active"]) &
            (segments_df["segment"].isin(["multi_year", "second_year_from_new",
                                           "second_year_regained"]))
        ]) /
        max(len(segments_df[
            segments_df["segment"].isin(["multi_year", "second_year_from_new",
                                          "second_year_regained"])
        ]), 1) * 100, 1
    )

    # Simpler overall retention: active retained (not new) / available (not new)
    not_new_available = segments_df[segments_df["segment"] != "new_donors"]
    not_new_active = not_new_available[not_new_available["is_active"]]
    overall_retention_v2 = round(
        len(not_new_active) / max(len(not_new_available), 1) * 100, 1
    )

    return {
        "analysis_year": analysis_year,
        "segments": segment_metrics,
        "totals": {
            "available_donors": total_available,
            "active_donors": total_active,
            "total_gifts": total_gifts,
            "total_revenue": round(total_revenue, 2),
            "gifts_per_active_donor": round(total_gifts / max(total_active, 1), 2),
            "average_gift": round(total_revenue / max(total_gifts, 1), 2),
            "revenue_per_active": round(total_revenue / max(total_active, 1), 2),
            "overall_retention_pct": overall_retention_v2,
        },
    }


# ── Donor File Growth ─────────────────────────────────────────────────────────

def compute_file_growth(
    segments_df: pd.DataFrame,
    analysis_year: int,
) -> dict:
    """
    Compute donor file growth metrics for the analysis year:
      - donors_active_last_year (available pool, not new)
      - new_donors_acquired
      - reactivated_donors
      - retained_donors
      - donors_active_this_year
    """
    new_ct = len(segments_df[segments_df["segment"] == "new_donors"])
    reactivated_ct = len(segments_df[
        (segments_df["segment"] == "second_year_regained") &
        (segments_df["is_active"])
    ]) + len(segments_df[
        (segments_df["segment"] == "lapsed_13_24") &
        (segments_df["is_active"])
    ]) + len(segments_df[
        (segments_df["segment"] == "multi_year_lapsed_25plus") &
        (segments_df["is_active"])
    ])

    retained_ct = len(segments_df[
        (segments_df["segment"].isin(["multi_year", "second_year_from_new"])) &
        (segments_df["is_active"])
    ])

    active_last_year = len(segments_df[
        segments_df["segment"].isin([
            "second_year_from_new", "multi_year",
            "second_year_regained", "lapsed_13_24",
        ])
    ])

    active_this_year = new_ct + reactivated_ct + retained_ct

    return {
        "donors_active_last_year": active_last_year,
        "new_donors_acquired": new_ct,
        "reactivated_donors": reactivated_ct,
        "retained_donors": retained_ct,
        "donors_active_this_year": active_this_year,
    }


# ── Growth Dynamics ───────────────────────────────────────────────────────────

def compute_growth_dynamics(
    segments_df: pd.DataFrame,
    analysis_year: int,
) -> dict:
    """
    Growth Dynamics (Win vs. Lapse Analysis).

    Breaks retained donors into:
      - Upgraded:   gave more in Y than Y-1
      - Downgraded: gave less in Y than Y-1
      - Same:       gave same amount in Y and Y-1

    Then computes:
      - Donors lapsed (available but inactive)
      - New donors acquired
      - Lapsed donors reactivated
      - Net win vs. lapse balance
    """
    # Retained = donors who gave in both Y-1 and Y (multi_year + second_year_from_new)
    retained_pool = segments_df[
        (segments_df["segment"].isin(["multi_year", "second_year_from_new"])) &
        (segments_df["is_active"])
    ].copy()

    if len(retained_pool) > 0:
        retained_pool["revenue_change"] = (
            retained_pool["analysis_year_revenue"] - retained_pool["prior_year_revenue"]
        )
        upgraded = retained_pool[retained_pool["revenue_change"] > 0]
        downgraded = retained_pool[retained_pool["revenue_change"] < 0]
        same = retained_pool[retained_pool["revenue_change"] == 0]
    else:
        upgraded = downgraded = same = pd.DataFrame()

    # Lapsed: available (not new) but did not give in Y
    lapsed = segments_df[
        (~segments_df["is_active"]) &
        (segments_df["segment"] != "new_donors")
    ]

    # New acquired
    new_donors = segments_df[segments_df["segment"] == "new_donors"]

    # Reactivated: lapsed segments that ARE active
    reactivated = segments_df[
        (segments_df["segment"].isin([
            "second_year_regained", "lapsed_13_24", "multi_year_lapsed_25plus"
        ])) &
        (segments_df["is_active"])
    ]

    # Revenue figures
    retained_rev_prior = float(retained_pool["prior_year_revenue"].sum()) if len(retained_pool) > 0 else 0
    retained_rev_current = float(retained_pool["analysis_year_revenue"].sum()) if len(retained_pool) > 0 else 0

    upgraded_rev_gain = float(upgraded["revenue_change"].sum()) if len(upgraded) > 0 else 0
    downgraded_rev_loss = float(downgraded["revenue_change"].sum()) if len(downgraded) > 0 else 0

    lapsed_rev_lost = float(lapsed["prior_year_revenue"].sum()) if len(lapsed) > 0 else 0
    new_rev = float(new_donors["analysis_year_revenue"].sum()) if len(new_donors) > 0 else 0
    reactivated_rev = float(reactivated["analysis_year_revenue"].sum()) if len(reactivated) > 0 else 0

    total_added = new_rev + reactivated_rev
    net_win_loss = retained_rev_current + total_added - retained_rev_prior - lapsed_rev_lost

    # Coverage Ratios (per DHC Growth Dynamics methodology, page 17 of sample)
    # Ratio 1: upgrade revenue gain / downgrade revenue loss
    coverage_retained = round(
        upgraded_rev_gain / max(abs(downgraded_rev_loss), 1), 2
    ) if downgraded_rev_loss != 0 else None

    # Ratio 2: new + reactivated revenue / lapsed revenue lost
    coverage_acquisition = round(
        total_added / max(lapsed_rev_lost, 1), 2
    ) if lapsed_rev_lost > 0 else None

    avg_gift_prior   = round(retained_rev_prior   / max(len(retained_pool), 1), 2)
    avg_gift_current = round(retained_rev_current / max(len(retained_pool), 1), 2)

    return {
        "retained_donors": {
            "count": len(retained_pool),
            "prior_year_revenue": round(retained_rev_prior, 2),
            "current_year_revenue": round(retained_rev_current, 2),
            "avg_gift_prior_year": avg_gift_prior,
            "avg_gift_current_year": avg_gift_current,
            "upgraded_count": len(upgraded),
            "upgraded_revenue_gain": round(upgraded_rev_gain, 2),
            "downgraded_count": len(downgraded),
            "downgraded_revenue_loss": round(downgraded_rev_loss, 2),
            "same_count": len(same),
            "coverage_ratio": coverage_retained,
        },
        "lapsed_donors": {
            "count": len(lapsed),
            "prior_year_revenue_lost": round(lapsed_rev_lost, 2),
        },
        "new_donors_acquired": {
            "count": len(new_donors),
            "revenue": round(new_rev, 2),
        },
        "reactivated_donors": {
            "count": len(reactivated),
            "revenue": round(reactivated_rev, 2),
        },
        "total_added": {
            "count": len(new_donors) + len(reactivated),
            "revenue": round(total_added, 2),
        },
        "net_win_loss_revenue": round(net_win_loss, 2),
        "win_vs_lapse": "WIN" if net_win_loss >= 0 else "LAPSE",
        "coverage_ratio_acquisition": coverage_acquisition,
    }


# ── Long-Term Value ───────────────────────────────────────────────────────────

def compute_ltv_projection(
    segments_df: pd.DataFrame,
    analysis_year: int,
    cost_of_acquisition: float = 74.0,
    projection_years: int = 5,
    annual_retention_rate: float = 0.45,
    revenue_growth_rate: float = 0.20,
) -> dict:
    """
    Project 5-year Long-Term Value for the new donor cohort.

    Uses simplified LTV model:
      - Year 1 Revenue per Donor = analysis year revenue / new donors
      - Each subsequent year: retained donors × revenue growth
      - ROI = cumulative revenue / cost of acquisition

    Defaults based on DHC sample benchmarks.
    """
    new_donors = segments_df[segments_df["segment"] == "new_donors"]
    count = len(new_donors)
    if count == 0:
        return {"error": "No new donors found in analysis year."}

    y1_revenue = float(new_donors["analysis_year_revenue"].sum())
    y1_revenue_per_donor = y1_revenue / count

    projections = []
    cumulative_revenue = 0.0
    current_revenue_per_donor = y1_revenue_per_donor

    for year_num in range(1, projection_years + 1):
        if year_num == 1:
            revenue_per_donor = current_revenue_per_donor
        else:
            # Retained donors generate higher revenue
            current_revenue_per_donor *= (1 + revenue_growth_rate)
            revenue_per_donor = current_revenue_per_donor * (annual_retention_rate ** (year_num - 1))

        cumulative_revenue += revenue_per_donor
        lt_roi = round(cumulative_revenue / cost_of_acquisition, 2) if cost_of_acquisition else 0

        projections.append({
            "year": year_num,
            "revenue_per_donor": round(revenue_per_donor, 2),
            "cumulative_revenue_per_donor": round(cumulative_revenue, 2),
            "lt_roi": lt_roi,
        })

    return {
        "new_donor_count": count,
        "first_year_revenue": round(y1_revenue, 2),
        "first_year_revenue_per_donor": round(y1_revenue_per_donor, 2),
        "cost_of_acquisition": cost_of_acquisition,
        "first_year_roi": round(y1_revenue_per_donor / cost_of_acquisition, 2),
        "projections": projections,
        "five_year_ltv": projections[-1]["cumulative_revenue_per_donor"] if projections else 0,
    }


# ── OHP Sentiment Overlay ─────────────────────────────────────────────────────

def compute_ohp_segment_summary(
    segments_df: pd.DataFrame,
    ohp_df: Optional[pd.DataFrame],
    segment_key: str,
    sentiment_column: Optional[str] = None,
    planned_giving_column: Optional[str] = None,
) -> dict:
    """
    Aggregate OHP interview themes and sentiment signals for a lifecycle segment.
    Returns a dict of OHP insights relevant to the segment.
    """
    if ohp_df is None or len(ohp_df) == 0:
        return {"available": False, "reason": "No OHP data loaded."}

    # Get donor IDs in this segment
    seg_ids = set(segments_df[segments_df["segment"] == segment_key].index)

    # Filter OHP data to segment donors
    # OHP df index should be account_id after merge
    ohp_segment = ohp_df[ohp_df.index.isin(seg_ids)] if ohp_df.index.name == "account_id" \
        else ohp_df[ohp_df.get("account_id", pd.Series()).isin(seg_ids)]

    total_in_segment = len(segments_df[segments_df["segment"] == segment_key])
    ohp_coverage = len(ohp_segment)
    coverage_pct = round(ohp_coverage / total_in_segment * 100, 1) if total_in_segment else 0

    result = {
        "available": True,
        "total_donors_in_segment": total_in_segment,
        "donors_with_ohp_interviews": ohp_coverage,
        "ohp_coverage_pct": coverage_pct,
    }

    # Sentiment score summary
    if sentiment_column and sentiment_column in ohp_segment.columns:
        scores = pd.to_numeric(ohp_segment[sentiment_column], errors="coerce").dropna()
        if len(scores) > 0:
            result["sentiment"] = {
                "mean": round(scores.mean(), 2),
                "median": round(scores.median(), 2),
                "high_engagement_pct": round((scores >= scores.quantile(0.75)).sum() / len(scores) * 100, 1),
            }

    # Planned giving signals
    if planned_giving_column and planned_giving_column in ohp_segment.columns:
        pg_col = ohp_segment[planned_giving_column]
        # Handle boolean, numeric, or categorical
        pg_positive = (
            pg_col.astype(str).str.lower().isin(["1", "true", "yes", "y", "high"])
        ).sum()
        result["planned_giving_signals"] = {
            "donors_with_signals": int(pg_positive),
            "pct_of_segment": round(pg_positive / total_in_segment * 100, 1) if total_in_segment else 0,
        }

    return result


# ── Large Gift Donors ($10k+) ─────────────────────────────────────────────────
# Per DHC methodology: donors with any single gift >= threshold are tracked
# SEPARATELY from the lifecycle analysis. Their revenue is reported as
# "Large Gift Donors" and added to General Revenue to get Total Revenue.
# This matches the JVW sample report (pages 4-6) exactly.

LARGE_GIFT_THRESHOLD = 10_000


def compute_large_gift_donors(
    df: pd.DataFrame,
    analysis_year: int,
    threshold: float = LARGE_GIFT_THRESHOLD,
) -> dict:
    """
    Identify donors with at least one gift >= threshold in the analysis year.

    Returns revenue breakdown:
      - large_gift_revenue: all revenue from these donors in analysis year
      - general_revenue:    revenue from all other donors
      - total_revenue:      general + large gift
      - pct_of_total:       large gift as % of total (matches DHC sample label
                            '% of General Revenue', which is actually % of total)
    """
    year_df = df[df["fiscal_year"] == analysis_year]
    if len(year_df) == 0:
        return {"threshold": threshold, "donor_count": 0, "revenue": 0.0,
                "general_revenue": 0.0, "total_revenue": 0.0, "pct_of_total": 0.0}

    large_ids = set(
        year_df[year_df["donation_amount"] >= threshold]["account_id"].unique()
    )

    large_rev  = float(year_df[year_df["account_id"].isin(large_ids)]["donation_amount"].sum())
    general_rev = float(year_df[~year_df["account_id"].isin(large_ids)]["donation_amount"].sum())
    total_rev   = general_rev + large_rev

    return {
        "threshold": threshold,
        "donor_count": len(large_ids),
        "revenue": round(large_rev, 2),
        "general_revenue": round(general_rev, 2),
        "total_revenue": round(total_rev, 2),
        "pct_of_total": round(large_rev / max(total_rev, 1) * 100, 1),
    }
