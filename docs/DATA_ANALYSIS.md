# Data analysis: `smb_leads.csv` and the registries

All numbers below are **observed** in the supplied synthetic data (5,000 leads created 2026-04-01 to 2026-06-30). Targets appear only in the final section and are labelled as proposals. Every figure is recomputed live by `backend/app/analytics.py` and shown in the Intelligence Console; `tests/test_journey.py::test_console_analytics_match_case_baseline` asserts the headline numbers.

## 1. The funnel, computed correctly

`stage_reached` is the *last* stage a lead reached, so counting it directly under-states every stage. A lead reached a stage if the stage's date column is filled; the dates are monotonic (0 violations checked).

| Stage | Leads reaching it | % of previous | % of all leads |
|---|---:|---:|---:|
| Lead | 5,000 | – | 100% |
| Contacted | 3,406 | 68.1% | 68.1% |
| Needs assessed | 1,974 | 58.0% | 39.5% |
| Quote accepted | 861 | **43.6%** | 17.2% |
| KYC complete | 588 | 68.3% | 11.8% |
| Activated | 368 | 62.6% | **7.4%** |

Average days between stages for activated customers: lead→contacted 2.0, →needs assessed 3.0, →quote accepted 4.1, →KYC 3.7, →activated 4.8; total **17.6 days**. Activated customers made **3.0** status-chasing calls on average.

## 2. Acquisition cost: two numbers that must not be confused

| Measure | Value | Meaning |
|---|---:|---|
| **Blended CAC** = Σ acquisition cost of *all 5,000 leads* ÷ 368 activations | **₹15,053** | What it really costs to win one customer |
| Mean `acquisition_cost_inr` on activated rows only | ₹5,385 | Ignores ₹3.56 M spent on leads that dropped. Wrong number to quote |
| Total quarterly acquisition spend | ₹55.4 lakh | |

## 3. Segments

| Segment | Leads | Contact | Needs | Quote | KYC | Activate | **Lead→Active** | Blended CAC | Median bundle ₹/mo | 6-m churn | NPS | Days |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| Micro retail & services | 2,709 | 68.4% | 54.4% | **32.2%** | **53.5%** | 63.2% | **4.1%** | **₹20,007** | ₹2,470 | **22.7%** | 7.0 | 16.6 |
| Professional offices | 1,247 | 69.3% | 62.3% | 53.0% | 74.4% | 65.1% | 11.1% | **₹10,695** | ₹6,575 | 13.8% | 6.9 | 16.9 |
| Small multi-site | 755 | 66.0% | 60.0% | 56.2% | 79.2% | 62.4% | 11.0% | ₹15,614 | **₹28,080** | 10.8% | 6.7 | 18.8 |
| Small manufacturers | 289 | 66.1% | 67.5% | 64.3% | 83.1% | **53.6%** | **12.8%** | ₹15,324 | ₹15,910 | **8.1%** | 6.5 | **20.5** |

Reading the table:

- **Professional offices** are the best first target: largest non-micro pool (25% of leads), lowest CAC, 2.7× micro conversion, healthy bundle value. Their losses sit in quote and KYC — exactly what an instant quote and Smart KYC fix.
- **Multi-site** businesses carry the highest value (median ₹28,080/month, 11× micro) and low churn. They need one bill, central management and site-by-site installation coordination: digital quote + field/partner install.
- **Manufacturers** convert best and churn least but are only 5.8% of leads; their weakest step is **KYC → activation (53.6%)** — leased-line installs (21-30 days) are the bottleneck, not selling.
- **Micro** is 54% of leads but converts at 4.1% with a ₹20,007 CAC against a ₹2,470/month bundle: field selling to micro destroys value. Its worst steps are needs→quote (32%) and quote→KYC (53%); 1,278 micro leads (47%) have no GSTIN. Micro must be served **self-service**, with cheap non-GST products (P04/P01, P07, P19, P22) and the field force kept away.

## 4. Lead sources

| Source | Leads | Lead→Active | Blended CAC | Comment |
|---|---:|---:|---:|---|
| Referral | 413 | **14.8%** | ₹4,099 | Best channel; formalise a referral programme |
| Inbound call | 504 | 9.5% | ₹5,113 | |
| Channel partner | 1,010 | 8.0% | ₹20,851 | Good conversion, expensive; give partners the advisor |
| Field sales | 1,720 | 7.3% | **₹24,335** | 55% of all spend for 34% of activations |
| Website form | 995 | 4.3% | ₹6,352 | Only 54.9% ever contacted: the form dead-ends |
| WhatsApp campaign | 358 | 2.8% | ₹4,026 | Only 41.3% contacted; the conversation stops at the first reply |

Digital sources are cheap but leak at the very first step, because today a human must call back. The advisor closes that gap.

## 5. Registrations

| | Leads | Lead→Active | Blended CAC |
|---|---:|---:|---:|
| Has GSTIN | 3,534 | **9.6%** | ₹12,686 |
| No GSTIN | 1,466 | **2.0%** | ₹41,728 |
| Has Udyam | 2,723 | 8.9% | ₹13,780 |
| No Udyam | 2,277 | 5.6% | ₹17,470 |

Leads without a GSTIN lose most at quote→KYC (24.7% vs 80.6%). 10 of 25 products require an active GSTIN, so the advisor must know GST status *before* quoting, not discover it at KYC.

GSTIN status of leads (mock registry): 3,266 Active, 167 Cancelled, 101 Suspended. **22 customers were activated on a cancelled or suspended GSTIN.**

## 6. Other dimensions

- **City tier**: tier 1 converts 8.6% vs tier 2 6.1%; the gap is almost entirely KYC→activation (72.7% vs 51.8%) — tier-2 installation capacity is the issue.
- **Current internet**: leased line 15.0%, mixed per site 12.7%, business broadband 9.3%, home broadband 7.6%, mobile hotspot 4.5%.
- **Turnover band**: < ₹40 lakh 3.9% → ₹5-25 cr 13.0%.
- **Follow-up calls vs outcome (activated)**: 1 call → 5.9% churn, NPS 7.5; 5 calls → 27.9% churn, NPS 6.0. Activation > 21 days → NPS 6.0 vs 7.2 within 14 days. Uncertainty after the sale drives churn; the tracker targets it.
- **Preferred language** varies conversion (Tamil 4.3%, Hindi 7.9%, English 8.0%). Groups are small and confounded with city and segment; this is evidence for *serving* regional languages, never for scoring people lower because of language.

## 7. Why leads drop (terminal reasons, 4,632 dropped leads)

| Funnel exit | Top reasons (count) | Addressed by SYNC? |
|---|---|---|
| Never contacted (1,594) | Unreachable after 3 attempts 805, not interested 470, wrong number 319 | Partly: a self-serve link replaces cold calling |
| After contact (1,432) | **Owner had no time for a visit 531**, locked in 325, **visit not scheduled by sales 296**, only wanted mobile 280 | **Yes**: no visit needed |
| After needs (1,113) | **Price too high 414**, competitor cheaper 207, **quote too complex 206**, **quote too slow 179**, decided to wait 107 | Yes / partly: instant, plain-language, budget-aware quote |
| After quote (273) | **Missing GST/Udyam doc 94, paperwork too long 79**, signatory unavailable 53, **details did not match 47** | Yes: registry lookup, 4 uploads, instant mismatch reasons |
| After KYC (220) | **Installation > 21 days 98**, cancelled before install 53, site not feasible 41, payment failed 28 | Partly: install-day estimate up front, tracker, pay-on-first-bill |

**1,432** drops are directly addressed and **1,806** partly addressed by the digital journey (classification in `analytics.DROP_LEVERS`).

## 8. What customers ask for vs what was sold

Most requested products of interest: P07 mobile (838), **P15 WhatsApp (827)**, **P22 guest Wi-Fi (814)**, **P14 SMS (813)**, P23 CCTV (787), P18 website (748). Most sold: P08 (192), P01 (180), P07 (176), P16 (175). WhatsApp was sold 54 times, SMS 27, Wi-Fi 62. The sales motion pitches connectivity; owners want customer-engagement tools. The advisor starts from stated needs.

## 9. Historical compliance leakage

Re-validating every activated bundle against today's catalogue rules (`analytics.historical_violations`): **56 of 368 bundles (15.2%) break a rule** — P03 1 Gbps fibre sold in tier-2 cities (24), WhatsApp API without an active GSTIN (9), Static IP without a fibre line (9), P03 below 5 employees (7), and others. A further 43 bundles include P01 for multi-site customers outside its listed target segments (a soft rule, see `PRODUCT_DECISIONS.md`). SYNC enforces every hard rule on the backend.

## 10. Data quality notes

- 124 leads have no `current_internet` / `current_provider`; treated as "Unknown".
- 147 leads report exactly ₹200 monthly telecom spend (138 micro) — looks like a floor/placeholder; not used for decisions.
- Activation dates run to 2026-07-26, after the 2026-07-15 reference date. The reference date is used only for document checks.
- June leads are right-censored (late-June leads had little time to activate); noted in the lead-score backtest.
- Lead ↔ registry joins are clean: every lead GSTIN/Udyam exists in its registry, names/states/cities match, no duplicates. All registry GSTINs pass the checksum and have `X` at PAN position 4.

## 11. Baselines and proposed pilot targets

| Metric | Observed baseline | **Proposed pilot target** (6-month pilot, prof + multi + micro self-serve) |
|---|---:|---:|
| Lead → activation | 7.4% | 12% |
| Lead → activation time | 17.6 days | ≤ 9 days |
| Blended CAC | ₹15,053 | ≤ ₹9,000 |
| Needs assessed → quote accepted | 43.6% | 60% |
| 6-month churn | 15.2% | ≤ 11% |
| Status chases per customer (supporting) | 3.0 | ≤ 1 |

Targets are proposals to be measured in an A/B pilot, not results.
