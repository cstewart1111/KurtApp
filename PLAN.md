# StoryCause DHC — Product Plan

Source documents: PCI SOW · StoryCause Data Guide · JVW DHC Lifecycle Sample

---

## v1.0 — Current (Deployed)

### ✅ Built and live

**Core pipeline**
- CSV ingestion with StoryCause 17-field data spec
- Column normalisation (flexible aliases — no exact names required)
- Deceased / bad address / gone away filtering (Data Guide field 8)
- Fiscal year assignment (configurable end month)
- OHP interview data join (optional second CSV)

**DHC lifecycle segmentation (PCI-owned logic)**
- New Donors
- 2nd Year from New
- Multi-Year Donors
- 2nd Year Regained
- Lapsed (13–24 Months)
- Multi-Year Lapsed (25+ Months)

**Metrics per segment (per DHC sample pages 3–6)**
- Available donors, Active donors
- % Donors Giving (retention)
- Gifts, Gifts/Active Donor
- Revenue, Average Gift
- Revenue/Active Donor, Revenue/Available Donor
- Conversion % (New Donors only: 2+ gifts same year)

**Summary KPIs (per DHC Summary tables, pages 4–5)**
- Overall Retention %
- Renewal (13–24) % ← explicitly named in sample
- Overall Frequency (gifts/donor)
- Average Gift
- Revenue/Active Donor

**Large Gift Donors ($10k+ threshold)**
- Tracked separately from lifecycle analysis (per DHC methodology)
- General Revenue (non-large-gift donors)
- Large Gift Donor count and revenue
- Total Revenue = General + Large Gift
- % of Total Revenue
- Displayed as its own Revenue Summary row in Overview

**Growth Dynamics (per sample page 17)**
- Retained / Upgraded / Same / Downgraded donor counts and revenue
- Lapsed donor count and revenue lost
- New donors acquired and revenue
- Reactivated donors and revenue
- Net Win/Loss revenue with WIN/LAPSE verdict
- Coverage Ratio: Upgrade revenue / Downgrade revenue
- Coverage Ratio: (New + Reactivated) / Lapsed revenue
- Avg gift per retained donor: prior year vs current year

**Long-Term Value (per sample page 18)**
- New donor cohort revenue (year 1)
- Cost of Acquisition (default $74)
- Year 1 ROI
- 5-year cumulative revenue projection per donor
- 5-year LTV

**AI features (Anthropic claude-sonnet-4-6)**
- Donor Road Map: segment-by-segment recommendations (strategic/conversational/executive)
- SOW Generator: tailored Statement of Work for prospect institutions

**Report outputs**
- Interactive dashboard (5 tabs: Overview, Lifecycle, Growth, Road Map, SOW)
- Downloadable Markdown report
- Data Quality Report (confidence score, flags, OHP coverage)
- Data Rules (inclusions/exclusions, fiscal year basis)

**Deployment**
- Vercel (Python serverless + Vite static)
- GitHub: cstewart1111/KurtApp
- Optional password protection (DASHBOARD_PASSWORD env var)

---

## v1.1 — Next Sprint

**Data ingestion**
- [ ] Two-file upload: accounts CSV + gifts CSV joined on account_id
      (Data Guide: "if more convenient to send account data in one file and gift data in another")
- [ ] Non-donor accounts in file (accounts with no gifts — important for org-level analysis)
- [ ] Sustainer/recurring donor flag analysis (Data Guide field 7)
      — Show % of each segment that are sustainers
      — Track sustainer retention separately
- [ ] Managed accounts flag (Data Guide field 6: Major Gift Officer assigned)
      — Flag these donors in segment tables
      — Exclude from mass outreach recommendations
- [ ] Acquisition origin channel breakdown (Data Guide field 9)
      — New donor source mix (Online, Direct Mail, Unsolicited, etc.)
      — Which channels produce the best 2nd-year retention

**Analytics**
- [ ] Mid-level / LAG donor tier (SOW requirement)
      — Define gift size tiers (e.g. $1k–$9,999 = mid-level, $250–$999 = lower mid)
      — Show as overlay on lifecycle segments (similar to Large Gift)
- [ ] 5-year trend charts per segment (lifecycle trends, sample pages 10–15)
      — Requires storing/accepting multi-year CSV history
      — Track retention, revenue, avg gift trend lines year-over-year
- [ ] Configurable Cost of Acquisition for LTV
      — Add to upload form as optional input (default $74)
- [ ] Frequency / recency scoring per segment

**UI**
- [ ] Segment trend sparklines (small inline charts per segment card)
- [ ] Multi-client comparison view (v1 is single-client; v1.1 adds switcher)

---

## v2.0 — Future

**Analytics**
- [ ] donorCentrics™ benchmark comparisons (sample page 16)
      — Overall Index and International Index benchmarks
      — Requires data licensing from donorCentrics / Target Analytics
      — Metrics: Rev/Donor, Avg Gift, Gifts/Donor, % New, Retention rates
- [ ] Predictive lapse scoring (which multi-year donors are at risk)
- [ ] Planned giving signal scoring (OHP intent + giving pattern)

**Visualization**
- [ ] Geographic Donor Map (sample page 19)
      — Heat map using city/zip from Data Guide fields 3
      — D3 choropleth or Google Maps integration
      — Requires city + zip in donor data

**Platform**
- [ ] Persistent storage (Vercel KV or Supabase) for session survival across restarts
- [ ] Multi-tenant: each client's analysis stored separately with access controls
- [ ] PDF export of full DHC report (branded StoryCause template)
- [ ] Scheduled auto-refresh (re-run analysis when new data uploaded)

---

## Source Document Traceability

| Feature | Source |
|---|---|
| 6 lifecycle segments | DHC Sample p3; SOW |
| Large Gift ($10k+) | DHC Sample p4–6; SOW "major donor segment" |
| Renewal (13–24) KPI | DHC Sample p4–5 (every summary table) |
| Coverage Ratio | DHC Sample p17 (Growth Dynamics) |
| LTV 5-year projection | DHC Sample p18 |
| Data Rules | DHC Sample p20 |
| Deceased filtering | Data Guide field 8 |
| 17-field CSV spec | Data Guide p1–2 |
| OHP interview join | SOW (combine interview data with giving history) |
| 10-year data request | SOW |
| AI road map | SOW "donor road map" deliverable |
| donorCentrics benchmarks | DHC Sample p16 (v2.0 — requires data access) |
| Geographic Donor Map | DHC Sample p19 (v2.0) |
| Sustainer analysis | Data Guide field 7 (v1.1) |
| Managed accounts | Data Guide field 6 (v1.1) |
| Mid-level/LAG segment | SOW (v1.1) |
| Two-file upload | Data Guide last paragraph (v1.1) |
| 5-year trend charts | DHC Sample p7–15 (v1.1) |
