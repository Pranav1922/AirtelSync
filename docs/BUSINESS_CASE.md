# Business case – SYNC Business

*All "observed" figures come from the supplied synthetic dataset. All targets and impact figures are **proposals** based on stated assumptions, not results.*

## 1. The problem in numbers (observed, Apr–Jun 2026)

- 5,000 leads → **368 activations (7.4%)**; steepest drop needs-assessed → quote-accepted (**43.6%**).
- **17.6 days** from lead to live service; **3 status-chasing calls** per customer.
- **Blended CAC ₹15,053** (₹55.4 lakh spend ÷ 368). Field sales: 55% of spend, 34% of activations, CAC ₹24,335.
- Micro businesses: 54% of leads, **4.1%** conversion, **₹20,007 CAC** for a **₹2,470/month** bundle.
- 1,432 drops (31%) are caused by things a digital journey removes outright: no time for a visit, visit never scheduled, slow or complex quote, missing documents, long paperwork, document mismatch.
- 56 of 368 activated bundles (15%) break catalogue rules; 22 customers activated on a cancelled/suspended GSTIN.

## 2. Target segments and priority

| Priority | Segment | Why | Motion |
|---|---|---|---|
| **1** | Professional offices (clinics, CA, law, coaching, agencies) | 25% of leads, lowest CAC (₹10,695), 11.1% conversion, losses at quote & KYC | Fully digital journey; partner/field only on callback |
| **2** | Small multi-site (chains of 3–12 sites) | Highest value (median ₹28,080/mo), 10.8% churn | Digital quote + KYC; field/partner for multi-site survey & install coordination |
| **3** | Micro retail & services | Volume (54%) but uneconomic to field-sell | **Self-service only**, Essential tier, non-GST products available, pay setup on first bill |
| **4** | Small manufacturers | Best conversion (12.8%) and churn (8.1%), small pool, install-bound | Digital quote + KYC; field engineer for leased-line delivery; IoT upsell |

## 3. Value proposition

**For the owner:** five questions in their language → three plans they understand, each product with a reason → one transparent monthly price (catalogue min, with max shown, no hidden discount) → four photos for KYC with instant, explained checks → a tracker with an expected date for every step.

**For Accel Business:** lower CAC (no visit for most leads), higher needs→quote conversion, zero eligibility leakage, a KYC exception queue instead of email chains, a re-engagement queue that tells field and partners which dropped leads to call and why.

## 4. Product bundles (catalogue IDs; price = catalogue minimum–maximum)

| Demo business | Recommended level and products | ₹/month | Setup | Ready in |
|---|---|---|---|---|
| Salon, 1 person, Jaipur (micro, budget ₹3,000) | **Essential**: P04 AirFiber, P07 Postpaid 299, P19 POS, P15 WhatsApp | ₹2,796–3,896 | ₹2,500 | 3 days |
| Dental clinic, 5 staff, Kolkata (prof) | **Growth**: P02 Fibre 300, 2× P08, 3× P16 email, 3× P20, 2× P12 telephony, P17 backup | ₹5,868–7,993 | ₹4,000 | 5 days |
| 11-store electronics chain, Visakhapatnam (multi) | **Growth**: 11× P02, 11× P09 failover, 11× P10 SD-WAN, 22× P23 CCTV, 4× P25 fleet, 3× P08 | ₹56,449–75,049 | ₹1,17,100 | 14 days |
| Furniture workshop, 15 staff, Nagpur (mfg) | **Growth**: P05 ILL 20, 2× P08, 4× P23, 2× P20, 4× P24 IoT, 3× P16 | ₹11,163–16,538 | ₹29,200 | 21 days |

(Exact bundles are generated live by the engine; the table shows the demo scenarios.)

## 5. Pricing approach

- Catalogue prices only; headline = sum of minimum prices × quantities; maximum shown as the ceiling; final rate confirmed after site check.
- Setup fees either paid up front (simulated) or added to the first bill — directly targets "first payment failed" (28 drops).
- Contract terms per product are shown; the longest term is labelled as the bundle commitment.
- No discounts are invented. A pilot could test bundle discounts as a separate, labelled experiment.

## 6. Expected impact (proposal – assumptions stated)

Assumptions: 5,000 leads per quarter, unchanged lead mix and mean bundle (₹12,351/month); micro field visits (894 leads, ₹1,601 each) replaced by the digital journey at website-form cost (₹274/lead).

| | Baseline (observed) | Pilot target |
|---|---:|---:|
| Activations / quarter | 368 | 600 (12%) |
| New MRR / quarterly cohort | ₹45.4 lakh | ₹74.1 lakh |
| Acquisition spend / quarter | ₹55.4 lakh | ≈ ₹43.5 lakh |
| Blended CAC | ₹15,053 | ≈ ₹7,250 (target ≤ ₹9,000 leaves headroom) |
| Days to activate | 17.6 | ≤ 9 (instant quote −4 days, instant KYC −3, no visit −3) |
| 6-month churn | 15.2% | ≤ 11% |

Incremental ≈ ₹28.7 lakh MRR per quarterly cohort ≈ **₹3.4 crore ARR per quarter of leads**, if the targets hold.

## 7. Field sales and partner integration

- **Partner code at checkout** attributes digital orders to the partner or executive who sent the link.
- **Re-engagement queue**: dropped leads with recoverable reasons, ranked by propensity × opportunity × recoverability, with owner (digital nudge / channel partner / field sales) and next action.
- **Callback queue**: "Talk to a person" on every screen creates a ticket with the advisor profile and step, in the owner's language.
- Field force focuses on multi-site surveys, leased-line installs and high-value manufacturers; partners handle local installation (consented address sharing).

## 8. Rollout plan

| Phase | Scope | Exit criteria |
|---|---|---|
| 0 – 6 weeks | Pilot build hardening: real GSP / Udyam API adapters, DigiLocker pull, e-sign, payment gateway, SSO for console | Security review, DPDP legal review, DPIA |
| 1 – 3 months | A/B pilot in 4 cities (2 tier-1, 2 tier-2), professional offices + micro self-serve; Hindi, Tamil, English | Metric deltas vs control on §6 |
| 2 – 3 months | Add multi-site and manufacturer flows with field integration; WhatsApp front end; Marathi, Kannada, Telugu, Bengali | CAC and days targets met |
| 3 | National rollout, partner portal, voice advisor | |

## 9. Risks and mitigations

| Risk | Mitigation |
|---|---|
| OCR errors on real-world photos | Confidence per field, checksum repair, manual-review routing, re-upload prompts |
| Over-reliance on automation for compliance | Hard rules on backend; every manual override needs a reason in the audit log |
| Channel conflict with partners/field | Partner codes, re-engagement queue routes leads to them, no commission loss |
| Price ranges feel uncertain | Min headline + max ceiling + "no discount applied"; site check confirms |
| Model bias | Protected proxies excluded; guardrail; backtest published; human decides |
| DPDP non-compliance | Consent-first, purpose-specific, 30-day image retention, withdrawal deletes immediately; legal review before launch |
| Tier-2 installation capacity (KYC→active 51.8%) | Expected dates set up front; AirFiber fallback (2 days) where fibre is not feasible |
