# Product catalogue analysis (`product_catalogue.csv`, 25 products)

| Category | Products |
|---|---|
| Connectivity (11) | P01 Fibre 100, P02 Fibre 300, P03 Fibre 1G, P04 5G AirFiber, P05 ILL 20, P06 ILL 100, P07 Postpaid 299, P08 Postpaid 599, P09 Failover, P10 SD-WAN, P11 Static IP |
| Communication (4) | P12 Cloud telephony, P13 Toll-free, P14 SMS 10k, P15 WhatsApp API |
| Cloud & productivity (4) | P16 Email & office, P17 Backup 1 TB, P18 Website, P19 Cloud POS |
| Security (3) | P20 Endpoint, P21 Managed firewall, P22 Secure Wi-Fi |
| IoT & physical (3) | P23 Cloud CCTV, P24 Machine IoT, P25 Fleet tracker |

## Eligibility rules (all enforced on the backend in `recommend.product_eligibility` / `validate_bundle`)

| Rule | Products |
|---|---|
| Tier 1 cities only | **P03** (every other product sells in tiers 1 and 2) |
| Minimum employees | P03 ≥ 5, P05 ≥ 10, **P06 ≥ 25**, P10 ≥ 10, P12 ≥ 3, P21 ≥ 10, P24 ≥ 10 |
| Minimum sites | **P10 ≥ 3** |
| Requires an *active* GSTIN | P03, P05, P06, P10, P12, P13, P14, P15, P21, P24 (10 products) |
| Requires one of (same bundle) | P09, P10, P21 → a fixed line (P01/02/03/05/06); P11 → fibre only (P01/02/03); P12, P23 → any internet line (P01-P06); P22 → P01-P04 |

Notable: Static IP (P11) cannot ride on a leased line or AirFiber; Secure Wi-Fi (P22) cannot ride on a leased line. The engine drops such add-ons with a visible reason.

## Price, term and install profile

| Product | ₹/month (min-max) | Setup | Min term | Install days |
|---|---|---:|---:|---:|
| P04 5G AirFiber | 899-1,099 | 0 | 6 | **2** |
| P01 Fibre 100 | 999-1,199 | 0 | 12 | 5 |
| P02 Fibre 300 | 1,499-1,799 | 0 | 12 | 5 |
| P03 Fibre 1G | 3,999-4,499 | 0 | 12 | 7 |
| P05 ILL 20 | 8,000-12,000 | 10,000 | 12 | **21** |
| P06 ILL 100 | 25,000-35,000 | 15,000 | **24** | **30** |
| P10 SD-WAN | 2,500-3,500 / site | 5,000 | 24 | 14 |
| P21 Firewall | 1,999-2,999 / site | 4,000 | 24 | 10 |
| P24 Machine IoT | 149-249 / device | 3,000 | 24 | 10 |
| P07 / P08 Postpaid | 299-399 / 599-799 | 0 | 1 | 1 |

Implications: the slowest product sets the activation date (leased lines dominate manufacturers' timelines); P04 is the fastest, cheapest answer for micro sites and the fallback when fibre is not feasible (41 historical drops). Prices are ranges, so the quote always shows min and max.

## Fit to segments (from `target_segments` and historical attach rates)

| Segment | Core | Typical add-ons (share of activated customers who bought it) |
|---|---|---|
| Micro | P04/P01 + P07 | P19 POS, P22 Wi-Fi, P23 CCTV, P15 WhatsApp (GSTIN needed) |
| Professional | P01/P02/P03 + P08 | P16 email (in 100% of prof bundles), P20, P17, P11, P12, P09 |
| Multi-site | P01/P02 per site + P08 | P09 per site, P10, P23 (2 per site), P19 per counter, P13 |
| Manufacturer | P05/P06/P03 + P08 | P16, P20, P24, P23, P21, P25 |
