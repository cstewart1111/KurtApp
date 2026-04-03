"""
StoryCause DHC — Lifecycle Segmentation Engine
PCI-owned donor lifecycle classification logic.

Six lifecycle segments (per DHC model):
  1. New Donors              — first gift ever in the analysis year
  2. 2nd Year from New       — acquired in Y-1, now in year 2
  3. Multi-Year Donors       — consecutive giving in Y-1 AND Y-2
  4. 2nd Year Regained       — lapsed before Y-1, reactivated in Y-1
  5. Lapsed (13-24 months)   — gave in Y-2 but NOT in Y-1
  6. Multi-Year Lapsed (25+) — last gift in Y-3 or earlier
"""
import pandas as pd
import numpy as np
from typing import Tuple, Optional


# Segment identifiers
SEGMENTS = {
    "new_donors": "New Donors",
    "second_year_from_new": "2nd Year from New",
    "multi_year": "Multi-Year Donors",
    "second_year_regained": "2nd Year Regained",
    "lapsed_13_24": "Lapsed (13–24 Months)",
    "multi_year_lapsed_25plus": "Multi-Year Lapsed (25+ Months)",
}

SEGMENT_ORDER = list(SEGMENTS.keys())


def get_fiscal_year(donation_date: pd.Timestamp, fiscal_year_end_month: int) -> int:
    """
    Return the fiscal year integer for a given donation date.

    If fiscal_year_end_month = 6 (June), then:
      - Gifts in Jul–Dec belong to the NEXT calendar year's FY
      - Gifts in Jan–Jun belong to the CURRENT calendar year's FY
    If fiscal_year_end_month = 12 (calendar year), FY == calendar year.
    """
    if fiscal_year_end_month == 12:
        return donation_date.year

    # Gift after fiscal year end month → belongs to the next fiscal year
    if donation_date.month > fiscal_year_end_month:
        return donation_date.year + 1
    else:
        return donation_date.year


def build_donor_summary(
    donor_df: pd.DataFrame,
    fiscal_year_end_month: int,
    date_column: str = "donation_date",
    amount_column: str = "donation_amount",
    account_id_column: str = "account_id",
) -> pd.DataFrame:
    """
    Aggregate the raw gift-level DataFrame into a donor-level summary.

    Returns a DataFrame indexed by account_id with columns:
        - years_given: set of fiscal years donor gave
        - first_year: earliest fiscal year of giving
        - last_year: most recent fiscal year of giving
        - total_revenue: lifetime giving total
        - total_gifts: lifetime gift count
        - yearly_revenue: dict {year: revenue}
        - yearly_gifts: dict {year: gift_count}
    """
    df = donor_df.copy()

    # Parse dates
    df[date_column] = pd.to_datetime(df[date_column], errors="coerce")
    df = df.dropna(subset=[date_column])

    # Assign fiscal year
    df["fiscal_year"] = df[date_column].apply(
        lambda d: get_fiscal_year(d, fiscal_year_end_month)
    )

    # Aggregate by donor × fiscal year
    yearly = (
        df.groupby([account_id_column, "fiscal_year"])
        .agg(
            year_revenue=(amount_column, "sum"),
            year_gifts=(amount_column, "count"),
        )
        .reset_index()
    )

    # Build donor-level summary
    donor_records = []
    for account_id, group in yearly.groupby(account_id_column):
        years_set = set(group["fiscal_year"].tolist())
        yearly_rev = dict(zip(group["fiscal_year"], group["year_revenue"]))
        yearly_cnt = dict(zip(group["fiscal_year"], group["year_gifts"]))
        donor_records.append(
            {
                account_id_column: account_id,
                "years_given": years_set,
                "first_year": min(years_set),
                "last_year": max(years_set),
                "total_revenue": sum(yearly_rev.values()),
                "total_gifts": sum(yearly_cnt.values()),
                "yearly_revenue": yearly_rev,
                "yearly_gifts": yearly_cnt,
            }
        )

    return pd.DataFrame(donor_records).set_index(account_id_column)


def assign_segment(row: pd.Series, Y: int) -> str:
    """
    Assign a single donor to their lifecycle segment for analysis year Y.

    Priority order matters — checked top to bottom:
      1. New Donors
      2. 2nd Year from New
      3. Multi-Year
      4. 2nd Year Regained
      5. Lapsed (13-24)
      6. Multi-Year Lapsed (25+)
      7. Unclassified (edge cases / data gaps)
    """
    years = row["years_given"]
    first_year = row["first_year"]
    last_year = row["last_year"]

    gave_Y   = Y     in years
    gave_Y1  = (Y-1) in years   # noqa: E221
    gave_Y2  = (Y-2) in years
    gave_Y3p = last_year <= (Y-3)   # last gift in Y-3 or earlier

    # 1. New Donors — first gift IN the analysis year
    if first_year == Y:
        return "new_donors"

    # 2. 2nd Year from New — acquired in Y-1
    if first_year == Y - 1:
        return "second_year_from_new"

    # 3. Multi-Year — gave in both Y-1 AND Y-2 (and have older history)
    if gave_Y1 and gave_Y2 and first_year < Y - 1:
        return "multi_year"

    # 4. 2nd Year Regained — lapsed before Y-1, reactivated in Y-1
    #    (gave in Y-1, did NOT give in Y-2, has history before Y-1)
    if gave_Y1 and not gave_Y2 and first_year < Y - 1:
        return "second_year_regained"

    # 5. Lapsed (13-24) — gave in Y-2 but NOT in Y-1
    if gave_Y2 and not gave_Y1:
        return "lapsed_13_24"

    # 6. Multi-Year Lapsed (25+) — last gift in Y-3 or earlier
    if gave_Y3p and not gave_Y1 and not gave_Y2:
        return "multi_year_lapsed_25plus"

    # Unclassified (shouldn't happen with clean data)
    return "unclassified"


def segment_donors(
    donor_summary_df: pd.DataFrame,
    analysis_year: int,
) -> pd.DataFrame:
    """
    Classify all donors into lifecycle segments for the given analysis year.

    Returns a copy of donor_summary_df with added columns:
        - segment:          segment key (e.g. 'new_donors')
        - segment_label:    human-readable label
        - is_available:     True if donor is in the available pool for their segment
        - is_active:        True if donor gave in the analysis year
        - analysis_year_revenue:  revenue in the analysis year (0 if inactive)
        - analysis_year_gifts:    gift count in the analysis year
    """
    df = donor_summary_df.copy()

    df["segment"] = df.apply(lambda row: assign_segment(row, analysis_year), axis=1)
    df["segment_label"] = df["segment"].map(SEGMENTS).fillna("Unclassified")
    df["is_active"] = df["years_given"].apply(lambda y: analysis_year in y)
    df["analysis_year_revenue"] = df["yearly_revenue"].apply(
        lambda d: d.get(analysis_year, 0.0)
    )
    df["analysis_year_gifts"] = df["yearly_gifts"].apply(
        lambda d: d.get(analysis_year, 0)
    )

    # Prior year revenue (for growth dynamics)
    df["prior_year_revenue"] = df["yearly_revenue"].apply(
        lambda d: d.get(analysis_year - 1, 0.0)
    )

    return df


def get_new_donor_conversion(
    segments_df: pd.DataFrame,
    account_id_column: str,
    analysis_year: int,
) -> dict:
    """
    For New Donors: compute conversion % (those who gave 2+ times in analysis year).
    New donors are 'active' by definition (first gift IS in Y).
    """
    new = segments_df[segments_df["segment"] == "new_donors"]
    total_acquired = len(new)
    if total_acquired == 0:
        return {"acquired": 0, "converted": 0, "conversion_pct": 0.0}

    converted = (new["analysis_year_gifts"] >= 2).sum()
    return {
        "acquired": int(total_acquired),
        "converted": int(converted),
        "conversion_pct": round(converted / total_acquired * 100, 1),
    }
