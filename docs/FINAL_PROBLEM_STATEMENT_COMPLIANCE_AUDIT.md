# Final problem-statement compliance audit

Audit date: 8 Nov 2026 · Source of truth: `6ad9d4887d445_airtel_sync/Airtel_SYNC_Case.pdf` (6 pages, re-read page by page and visually rendered) · No application code was changed during this audit · The demo database `backend/var/sync.db` was not modified (live tests ran against a copy on a separate port).

---

## 1. Executive summary

**Verdict: PARTIALLY COMPLIANT.**

The **product** meets all four mandatory build items on PDF page 3 (Advisor, Quote and checkout, Smart KYC, Tracker), uses all supplied data, and catches every planted KYC problem I could find by inspection. Two of the three stretch goals are delivered, one of them only partly. The business-case deck, architecture diagram and privacy note exist.

Four things prevent a "substantially compliant" verdict:

1. **Two mandatory submission items are missing** (PDF p.4, item 1): there is **no demo video** and **no code repository** (the folder is not a git repository and has no remote).
2. **"In their preferred language"** (p.3, problem statement) is only half-delivered. The interface is translated into Hindi and Tamil, but every backend-generated sentence stays in English: plan reasons, eligibility notes, KYC check details, delay reasons and pending actions. A Hindi user still sees English explanations.
3. **"A GenAI-powered assistant"** (p.3, build challenge): by default the advisor is a rule-based slot-filler. The optional LLM path has never been run with a real key. The judges will run **15 live advisor scenarios** (p.4 footnote), and simple phrasings such as "we make furniture" or "twenty people" are not understood.
4. **Live testing found three integrity and privacy defects**, plus inaccurate claims in the privacy note (§9).

All of these can be fixed in roughly 1–2 working days, as set out in `docs/COMPLIANCE_REMEDIATION_PLAN.md`.

## 2. Requirement coverage statistics

| Status | Count | % of 57 |
|---|---:|---:|
| Fully implemented | 34 | 59.6% |
| Partially implemented | 12 | 21.1% |
| Mocked / simulated (transparent, permitted by the brief) | 5 | 8.8% |
| Documented only | 0 | 0% |
| Not implemented | 5 | 8.8% |
| Not verifiable | 1 | 1.8% |

Mocked items are **not** counted as fully implemented. Of the 5 not-implemented items, 2 are mandatory (video, repository) and 3 are optional (voice, WhatsApp, DigiLocker/e-sign).

## 3. Traceability matrix

Priority: **M** = mandatory (problem statement, build challenge or "What teams submit"), **I** = important (key questions, context, data use), **O** = optional (stretch goals or "e.g." examples).

| ID | Requirement | PDF p. | Pri | Expected behaviour | Implementation | Evidence | Status | Gap | Recommendation |
|---|---|---|---|---|---|---|---|---|---|
| R01 | Working prototype + short business case; assessed on technical depth and business judgement | 2 | M | Runnable prototype and business case | `backend/`, `frontend/`, `submission/SYNC_Business_Case.pptx` | Tests 45/45, build OK, live run | FULLY | — | — |
| R02 | Fictional operator, synthetic data; not company data | 2 | M | No claim of real Airtel/Accel services or real data | Footer `i18n/*.ts` `footer.note`, README banner | UI footer, README | FULLY | — | — |
| R03 | Pain: needs discovered by a sales visit that pushes monthly targets | 2 | I | Unbiased self-service needs discovery | `backend/app/advisor.py`, `recommend.py` | Live journeys 1–4 | FULLY | — | — |
| R04 | Pain: quote takes 3–5 days, with product codes the owner doesn't understand | 2 | I | Instant plain-language quote | `quote.py`, `frontend/src/pages/Quote.tsx` | `/api/quote/price` < 0.3 s; product names and reasons shown | FULLY | — | — |
| R05 | Pain: KYC collected physically or by email | 2 | I | Digital upload | `kyc/service.py`, `pages/Kyc.tsx` | Upload + specimen tests | FULLY | — | — |
| R06 | Pain: install 10–14 days with 3–4 follow-up calls | 2 | I | Expected dates, fewer chases | `orders.py` `expected_dates`, `pages/Track.tsx` | Journey 10 | MOCKED | Serviceability and installation advance by a demo button | Keep; label as simulated in the demo (already done) |
| R07 | Pain: each product billed and supported separately | 2 | I | One bill, one point of support | One quote/order per bundle; `/api/handoff` | Order holds all lines | PARTIAL | No billing; reasons say "on one bill" (`recommend.py`) | Say "one order / one quote" or add a "single consolidated bill (proposed)" note; no build needed |
| R08 | Competitors offer instant online sign-up | 2 | I | Instant digital sign-up | Full journey | Journey 1 end to end | FULLY | — | — |
| R09 | Digital-first journey: discover the right bundle, buy it, get it activated with minimal human effort | 3 | M | End to end without a salesperson | All pages + API | Journey 1 reached `activated` | FULLY | Activation simulated (R06) | — |
| R10 | …on a phone | 3 | M | Mobile-first UI | Tailwind responsive layouts | 375 px check earlier; header fixed | FULLY | No full mobile pass on every page during this audit | Do a 375 px pass on Quote, KYC and Console before recording |
| R11 | …in their preferred language | 3 | M | Whole journey in the owner's language | `frontend/src/i18n/{en,hi,ta}.ts`; advisor keyword lexicons | Hindi session: plan reason returned "Main internet line for 1 site, replacing your current mobile hotspot." | PARTIAL | Backend text is English-only: reasons, notes, pitch, pricing explanation, KYC details, delay reasons, pending actions, API errors; business-type and city chips untranslated; Console English-only; 7 dataset languages unsupported | Return reason **codes + params** from the backend and translate in the frontend (see H1) |
| R12 | KQ1: which segments first, and what bundle (products, price point, **contract length**) for each | 3 | I | Priority + bundle per segment | `docs/BUSINESS_CASE.md` §2, §4; deck slide 3 | Doc review | PARTIAL | Contract length per segment bundle not stated | Add a commitment column to BUSINESS_CASE §4 and deck slide 3 |
| R13 | KQ2: advisor chat **or voice**, in Hindi and regional languages, asks a few questions, recommends a bundle with a clear monthly price | 3 | I | Conversational discovery | `advisor.py`, `pages/Advisor.tsx` | Hindi and Tamil scripts pass (`test_advisor_hindi_and_tamil`) | PARTIAL | Hindi + Tamil only; no voice; see R11 | Language fix (H1); voice optional |
| R14 | KQ3: near-instant KYC (GSTIN/Udyam lookup, OCR) | 3 | I | Seconds, not days | `kyc/ocr.py`, `pipeline.py`, `validators.py` | Load + verify in ~1.3 s | MOCKED | Lookups are against the supplied mock CSVs (as the brief intends) | Keep; disclaimer already shown |
| R15 | KQ3: DPDP **consent** | 3 | M | Free, specific, affirmative consent | `kyc/service.py` `record_consent`; `pages/Consent.tsx` | Upload refused without consent (test) | PARTIAL | **Optional "share with installation partner" is pre-ticked** (`Consent.tsx:19`) — not affirmative consent | Default every optional purpose to `false` |
| R16 | KQ3: purpose limitation | 3 | M | Per-purpose consent records | `consent_records` table | 4 purposes stored with timestamp, version, language | FULLY | Only the KYC purpose is enforced; partner sharing isn't implemented, so its consent has nothing to gate | — |
| R17 | KQ3: data minimisation | 3 | M | Collect only what is needed | Advisor slots; `CheckoutIn` | No phone or email collected | FULLY | — | — |
| R18 | KQ4: field force and channel partners add to, not compete with, the digital journey | 3 | I | Concrete hand-offs and attribution | `analytics.priority_queue` (owner routing), `/api/handoff`, console Assistance tab, `partner_code` on orders | Console screens; handoff test | PARTIAL | `partner_code` is stored but never shown or used; "Assign to partner" assigns a fixed string; no partner-facing view; queue has no action buttons | Show the partner code in console Orders + a per-partner count; take the assignee name from an input |
| R19 | KQ5: define 3–5 metrics with targets | 3 | M | Baselines + targets, clearly separated | `pages/Console.tsx` TARGETS; `DATA_ANALYSIS.md` §11 | Console shows "observed" vs "Target" badges | FULLY | — | — |
| R20 | Advisor is **GenAI-powered** | 3 | M | Generative or LLM understanding | `advisor.py` (rules), `llm.py` (optional) | `health.llm=false`; LLM path never executed | PARTIAL | Rule-based by default; LLM untested; misses "we make furniture", "twenty people", "I don't know" | Test the LLM path with a key; widen the rule lexicon; show "AI on/off" honestly (H2) |
| R21 | Advisor asks about type, size, locations, current tools | 3 | M | Those slots captured | `advisor.SLOTS` | Profile card; journeys | FULLY | Shows "People: 1" before the question is asked (default in `public_profile`) | Don't default the displayed employee count |
| R22 | Recommends a bundle **from the product catalogue** | 3 | M | Only real IDs, eligible | `recommend.py`, `data.catalogue()` | Bundles 2–4 had zero validation errors | FULLY | — | — |
| R23 | Explains why, in plain language | 3 | M | Reason per product | `recommend.build_level` reasons | Plans page | FULLY | English only (see R11) | — |
| R24 | **A single, transparent monthly price** | 3 | M | One headline monthly figure | `quote.price_items`; Plans/Quote show "from ₹min, up to ₹max" | UI | PARTIAL / ambiguous | The catalogue gives a price range; we show a range, so the "single price" is a "from" price | Adopt and state one price rule (e.g. price at catalogue minimum, locked once KYC passes), show that single number, keep the range in the explanation |
| R25 | Add-ons the owner can toggle | 3 | M | Add, remove, change quantity, live price | `pages/Quote.tsx`, `/api/quote/price`, `/api/eligibility` | Dependency error shown live | FULLY | — | — |
| R26 | Checkout | 3 | M | Order created from the quote | `orders.checkout` | Journeys 1, 6–8 | FULLY | — | — |
| R27 | Payment at checkout | 3 | M | Pay or defer setup fee | `orders.checkout` payment_mode | "Simulated payment" text | MOCKED | No gateway | Keep; labelled |
| R28 | Smart KYC: document upload | 3 | M | Upload with validation | `/api/kyc/{case}/documents` | Rejects non-image and > 8 MB (live) | FULLY | — | — |
| R29 | Smart KYC: extraction | 3 | M | OCR fields with confidence | `kyc/ocr.py`, `pipeline.extract_fields` | `test_document_type_recognition_and_field_extraction` | FULLY | — | — |
| R30 | Smart KYC: validation | 3 | M | Cross-checks with reasons | `pipeline.verify` | 12 applicants match manual inspection | FULLY | — | — |
| R31 | KYC case integrity (implied by validation and the tracker) | 3 | M | A verified case can't be silently altered | `kyc/service.py` | **Live: a blocked specimen load deleted all 4 document rows of a passed case**; reviewer reject on an activated order set "KYC was not approved" | PARTIAL | `load_specimen` deletes before the lock check; `upload` replace orphans the old file; `decide` ignores the order stage | Check the lock/consent before any delete; delete files with rows; refuse decisions unless the order stage is `kyc` (C3, H3) |
| R32 | Mocked GSTIN lookup | 3 | M | Lookup incl. status | `validators.lookup_gstin` → `mock_gstin_registry.csv` | Cancelled/suspended tests | MOCKED (as requested) | — | — |
| R33 | Mocked Udyam lookup | 3 | M | Lookup | `validators.lookup_udyam` → `mock_udyam_registry.csv` | Tests | MOCKED (as requested) | — | — |
| R34 | A clear consent screen | 3 | M | Explains what, why, who, how long, withdrawal | `pages/Consent.tsx` | UI | PARTIAL | Pre-ticked optional box; says images are deleted "30 days after **verification**" but code purges 30 days after **upload** (`service.py:102`) | Untick by default; align the text |
| R35 | Tracker: status the owner checks instead of calling support | 3 | M | Current stage, dates, history, pending actions | `orders.get_order`, `pages/Track.tsx` | Journey 10 | FULLY | Withdraw link still shown after activation and puts a live order "on hold" | Hide withdraw after activation or handle that state |
| R36 | Stretch: voice front end | 3 | O | Voice | — | — | NOT | — | Optional |
| R37 | Stretch: WhatsApp front end | 3 | O | WhatsApp | — | — | NOT | — | Optional |
| R38 | Stretch: back-office view of **leads the advisor could not close** | 3 | O | List of live advisor sessions/quotes that didn't convert | Console "Lead priority" (historical CSV drops) + Assistance queue | Console | PARTIAL | Abandoned **live** advisor sessions and draft quotes are not listed anywhere | Add "Unconverted advisor sessions" to the console (H4) |
| R39 | Stretch: simple propensity score for which leads to call | 3 | O | Score + reasons | `analytics.score_model`, `priority_queue` | AUC 0.686 time split; reasons per row | FULLY | — | — |
| R40 | Submit: working prototype | 4 | M | Runs locally | README commands | Server start + health OK | FULLY | — | — |
| R41 | Submit: **demo video ≤ 3 minutes** | 4 | M | Recorded video | `docs/THREE_MINUTE_DEMO_SCRIPT.md` only | No video file | NOT | Not recorded | Record after fixes C3–C5 and H1 (C2) |
| R42 | Submit: **code repository** | 4 | M | Shareable repository | — | No `.git`, no remote | NOT | Missing | `git init`, commit, push to GitHub (C1) |
| R43 | Submit: architecture diagram with components and data flows | 4 | M | Diagram | `docs/SOLUTION_ARCHITECTURE.md` (Mermaid), deck slide 7 | Doc + deck | FULLY | Mermaid needs rendering; no standalone image | Export a PNG/PDF of the component + flow diagram |
| R44 | Submit: business case ≤ 10 slides covering target customer, value, pricing or savings, rollout, risks | 4 | M | ≤ 10 slides | `submission/SYNC_Business_Case.pptx` (10 slides) | Validated; content checked | FULLY | Contract length per segment missing (R12) | — |
| R45 | Submit: 1-page privacy and security note | 4 | M | Accurate one-pager | `docs/PRIVACY_AND_SECURITY.md` (536 words) | Doc review vs code | PARTIAL | Inaccurate claims: order IDs "unguessable" (order no. = 6 hex chars); "LLM never receives identifiers" (the fallback sends the raw message); retention wording; reset endpoint has no auth | Correct the claims or fix the code (C5); export to a one-page PDF |
| R46 | Use catalogue for advisor and quotes: price ranges, setup fees, contract length, eligibility, dependencies | 4 | M | All fields used | `data.Product`, `recommend.py`, `quote.py` | `test_products.py` (13 tests) | FULLY | — | — |
| R47 | Use smb_leads.csv | 4 | I | Analytics from data | `analytics.py` | Independent `csv`-module recomputation matches | FULLY | — | — |
| R48 | GSTIN registry backing, incl. cancelled/suspended | 4 | M | Status-aware | `lookup_gstin`, `gstin_ok` | Journey 8 blocks GST products at the advisor | FULLY | — | — |
| R49 | Udyam registry backing | 4 | M | Lookup | `lookup_udyam` | Tests | FULLY | — | — |
| R50 | KYC specimens for OCR and validation; "some contain planted problems" | 4 | M | Catch the planted problems | `pipeline.py`; `docs/KYC_DOCUMENT_ANALYSIS.md` | 7 problem packs flagged, 5 clean packs pass | FULLY | Unknown planted signals in the judges' key can't be checked | — |
| R51 | Judges' pack must not be used | 4 | M | Not used | — | No such file in the repo | FULLY | — | — |
| R52 | Judges run 15 advisor test scenarios live | 4 | M (implied) | Advisor robust to unseen phrasings | `advisor.py` | 5 probes: 2 fully handled, 1 partly (city kept, number word missed), 2 not understood | NOT VERIFIABLE | The scenarios are unknown; rule coverage is limited | Widen lexicons + LLM fallback + a "pick from options" safety net (H2) |
| R53 | Baselines consistent with Appendix A1 (5,000 → 368, 17.6 days, 3 chases, ₹15,000, 9.6% vs 2.0%, ₹6,900 median, micro ~₹2,500) | 5 | I | Same figures | `analytics.overview` | Recomputed: 15,053 / 17.6 / 3.01 / 9.6 / 2.0 / 6,900 / 2,470 | FULLY | — | — |
| R54 | Segment needs per Appendix A2 (micro UPI/POS, WhatsApp; prof uptime, cloud email/storage, security; multi one bill, central management, CCTV, failover; mfg dedicated bandwidth, IoT, ERP access) | 6 | I | Bundles address them | `recommend.SEGMENT_ADDONS`, `CONNECTIVITY` | Journeys 2–4 | FULLY | "ERP access" maps only to connectivity (no ERP product in the catalogue) | Mention it in the reason text for manufacturers |
| R55 | Price sensitivity by segment | 6 | I | Budget-aware, cheap micro plan | Budget logic; Essential for micro | Micro plan ₹2,096 within ₹2,500 budget | FULLY | — | — |
| R56 | Dataset README rules (ref. date 2026-07-15, PAN 'X', district 00, 90-day bill, GST statuses) | 4 (README referenced) | M | Applied | `config.py`, `validators.py`, `pipeline.py` | 90/91-day boundary test | FULLY | — | — |
| R57 | KQ3 examples: DigiLocker, e-sign | 3 | O | Optional | — (documented as future adapters) | — | NOT | — | Optional; keep as "not connected" |

**Ambiguity flagged:** R24's "single, transparent monthly price" conflicts with a catalogue that only gives min–max ranges. A documented rule is required; see the remediation plan. The PDF contains **no explicit scoring rubric**. The only stated basis is "technical depth and business judgement together" (p.2).

## 4. Functional audit results

**A. Acquisition and onboarding — works.**
- A new business can enter from the landing page or a demo scenario; all four segments are supported; the journey is advisor → plans → quote → checkout → consent → KYC → tracker, with no dead ends.
- Help is available on every screen (`HelpDrawer` → `/api/handoff`).
- Weakness: language (R11).

**B. AI advisor — a predefined workflow with good extraction, not genuinely generative.**
- It scans each message for every slot (one sentence filled type, city, size and tier).
- Follow-up questions are in a fixed order.
- It considers employees, sites, segment, tier, budget, current internet and GST status.
- It works without an LLM key.
- Conflicting information (e.g. "Actually we have 30 staff") silently overwrites the earlier answer, with no confirmation.
- Probe results:

| Phrase | Result |
|---|---|
| "I run a small shop" | understood (micro) |
| "we make furniture" | **not understood** |
| "office in Bangalore with twenty people" | city understood, number word ignored |
| "I don't know" (internet question) | **not understood**; question repeated |

**C. Recommendation and quote — correct.**
- All 25 products load.
- City-tier, employee, site, GSTIN-status and dependency rules are enforced on the backend.
- An ineligible quote is rejected server-side (HTTP 422).
- Prices are catalogue × quantity, with no discounts.
- Setup fees, longest commitment and slowest-install days are shown.
- All four segment probes produced eligible bundles:

| Segment probe | Recommended plan | From |
|---|---|---|
| Micro, Patna | Essential: P04, 2× P07, P19 | ₹2,096 |
| Multi, Pune | Growth, 6 sites (incl. SD-WAN) | ₹31,173 |
| Manufacturer, Surat (120 staff) | Growth with ILL 20, IoT ×15, firewall | ₹21,557 |
| Clinic (prof), Kolkata | Growth | ₹5,868 |

- `target_segments` is used as a soft rule, by design (it isn't an eligibility rule in the README).
- Edge case: a dependency counts as satisfied by an ineligible product (P09 with an ineligible P03). The quote is still rejected because of P03, so the impact is low.

**D. Smart KYC — the logic is correct; lifecycle integrity is not.**
- Present and working: upload, type/size validation, classification, OCR with per-field confidence, GSTIN format + checksum + OCR repair, registry status, Udyam format + lookup, name/address/signatory/freshness checks, missing-document detection, specimen watermark detection, manual-review routing, clear status.
- Results by applicant (independent inspection = engine output):

| Applicants | Engine result |
|---|---|
| K02, K03, K08, K09, K12 | Pass |
| K04, K10 | Manual review |
| K01, K05, K06, K07, K11 | Action required |

- **Defects:**
  1. A specimen load on a locked (passed) case deletes the document rows before refusing.
  2. Replacing a document deletes its row but leaves the old file on disk, outside the retention purge.
  3. The same image uploaded under two document types isn't detected as a duplicate. A mismatched type is caught only when the detected type differs.
- False-negative risk: Udyam date/activity differences are logged as "info" only.
- False-positive risk: low; OCR repair requires both the checksum and the registry to agree.

**E. Privacy and security.**
- Implemented and verified:
  - Purpose-wise consent with timestamps, notice version and language.
  - Withdrawal deletes files and fields.
  - Identifier masking in API responses, chat and logs (log filter fixed and checked).
  - Uploads validated by magic bytes and an 8 MB cap, stored under random filenames.
  - Purge on start-up.
  - Console key required on console routes.
  - Path traversal is not possible through the SPA fallback.
  - No secrets in the repo.
- Gaps:
  - Pre-ticked optional consent.
  - `POST /api/demo/reset`, `POST /api/orders/{id}/advance` and the document-image route need no authentication.
  - Order numbers have only 24 bits of entropy.
  - The LLM fallback would send the raw user message.
  - Raw advisor transcripts (which can include a GSTIN) are stored unmasked in SQLite.
  - The purge runs only at start-up.
- DPDP: the design follows consent, purpose-limitation, minimisation and withdrawal principles. This is **not legal compliance**: no grievance officer, no access/erasure request flow, no DPIA, no breach process.

**F. Orders — work, with two state bugs.**
- Quote acceptance, checkout, persistence, events, the KYC gate (advance refused until KYC passes; refused again during manual review), simulated serviceability and installation, activation, delay handling with a revised date, and indicative timelines all work. Incomplete KYC holds the order at the KYC stage with a reason and pending actions.
- Bugs: a reviewer decision and a consent withdrawal on an **activated** order write a misleading delay reason.

**G. Field sales and partners.**

| Capability | Status |
|---|---|
| Priority queue with owner routing and next action | Implemented, read-only, historical data |
| Callback queue with profile context | Implemented |
| Partner code at checkout | Stored but unused |
| Partner portal, assignment by name, partner attribution | Not implemented |

**H. Analytics — accurate.**
- Funnel, segment, source, drop reasons, blended vs activated-only CAC, days, churn, NPS and the compliance audit match an independent recomputation from the raw CSVs.
- Targets are visually separated from observed values.
- The KYC exception queue and orders list are live from the database.
- No random or fabricated analytics.
- The landing-page stats and chat preview are **hard-coded** text. Their values are correct, but they aren't computed.

## 5. Technical audit results

| Check | Result |
|---|---|
| `python3 -m pytest backend/tests -q` | **45 passed** (8.4 s) |
| `npm --prefix frontend run build` | **OK** (TypeScript strict, Vite 6) |
| Backend start-up + `/api/health` | OK: OCR available, 25 products, 5,000 leads, LLM disabled |
| Live audit script (copied DB, port 8010) | **22 pass, 2 fail, 8 observations** — failures: reviewer reject on an activated order is accepted; dependency satisfied by an ineligible product |
| Earlier bug fixed this week | Log filter broke `%d` formatting → fixed; verified |
| Response times | Every API step < 1.5 s, cold OCR ~1.1 s |
| Architecture | Clear module separation (advisor, recommend, quote, orders, KYC, analytics, data, db) |
| Scalability | Single process, global SQLite lock, in-memory caches: fine for a demo, not for production (documented) |
| Dependencies | `backend/requirements.txt` (unpinned minimums); `frontend/package.json` (caret ranges) |
| Accessibility | Labels/ARIA on key controls, keyboard-reachable; no formal WCAG audit done |
| Dead or placeholder UI | None found; console "Advance" swallows API errors silently |
| Test-coverage gaps | No test for lock-bypass deletion, decisions after activation, consent defaults, or frontend behaviour |

Live journey results:

| # | Journey | Result |
|---|---|---|
| 1 | Dental clinic, full journey | PASS (Growth, K02 passed, activated) |
| 2 | Micro retail | PASS |
| 3 | Multi-site | PASS |
| 4 | Small manufacturer | PASS |
| 5 | KYC success | PASS |
| 6 | Manual review (K10) | PASS; advance blocked |
| 7 | Missing document (K05) | PASS |
| 8 | Cancelled GSTIN (K01) | PASS: GST products blocked in the advisor, KYC action required |
| 9 | Ineligible selection | PASS (rejected server-side) |
| 10 | Tracking | PASS |

## 6. Dataset validation

Recomputed with the standard-library `csv` module (independent of app code):

- Funnel: 5,000 / 3,406 / 1,974 / 861 / 588 / 368.
- Blended CAC ₹15,053 vs ₹5,385 on activated leads only.
- 17.6 days to activate; 3.01 follow-up calls.
- Median bundle ₹6,900; 6-month churn 15.2%; NPS 6.86.
- Activation with GSTIN 9.6%, without 2.0%; needs → quote 43.6%.
- Segment conversion / blended CAC / median bundle:

| Segment | Lead → live | Blended CAC | Median ₹/mo |
|---|---:|---:|---:|
| Micro | 4.1% | ₹20,007 | ₹2,470 |
| Professional | 11.1% | ₹10,695 | ₹6,575 |
| Multi-site | 11.0% | ₹15,614 | ₹28,080 |
| Manufacturer | 12.8% | ₹15,324 | ₹15,910 |

- GSTIN registry: 3,266 active, 167 cancelled, 101 suspended; 22 customers were activated on a non-active GSTIN.

All match the app, the docs and Appendix A1. Known data issues (documented in `DATA_ANALYSIS.md` §10): 124 missing values for current internet; 147 leads with exactly ₹200 spend; activation dates later than the reference date; June right-censoring; Udyam certificate dates differ from the registry.

## 7. Privacy and security audit (summary)

| Implemented (verified) | Limitation / risk |
|---|---|
| Consent before upload, 4 purposes, timestamp, version, language | Optional purpose pre-ticked |
| Withdrawal deletes images and fields | Allowed after activation; puts a live order "on hold" |
| Masking in API, chat, console, logs | Raw transcripts in the DB unmasked; LLM fallback sends the raw message |
| Magic-byte type check, 8 MB cap, random filenames | Replaced or wiped documents leave orphan files; image route needs no auth |
| 30-day purge | Only on start-up; consent text says "after verification" |
| Console key | Shared key; reset and advance endpoints need no auth |
| Server-side price and eligibility re-validation | — |
| No secrets in the repo | — |

## 8. Submission readiness

| Deliverable (p.4) | State | Ready? |
|---|---|---|
| 1a Working prototype | Runs; 45 tests pass | Yes, after C3–C5 |
| 1b Demo video ≤ 3 min | Script only | **No** |
| 1c Code repository | No git repository or remote | **No** |
| 2 Architecture diagram | Mermaid in markdown + deck slide 7 | Mostly (export an image) |
| 3 Business case ≤ 10 slides | 10 slides, validated, consistent figures | Yes (add contract length) |
| 4 1-page privacy note | 536 words | **No**: fix 3 inaccurate claims, export as PDF |

Template check: `Submission Template_Sync.pptx` has only 2 slides (a cover background and a content background), no required slide structure, and is unmodified (22 Oct timestamp). The deck reuses its backgrounds.

Demo-script accuracy: the steps match the current UI; the "41% of similar offices" reason and K02 pre-selection were confirmed live.

## 9. Critical and high-priority gaps (fix in this order)

| Rank | ID | Gap | Severity | Complexity |
|---|---|---|---|---|
| 1 | C1 | No code repository (R42) | CRITICAL | Low |
| 2 | C3 | KYC lock bypass deletes a verified case's documents; replaced documents leave orphan files (R31) | CRITICAL | Low |
| 3 | C4 | Optional consent pre-ticked (R15, R34) | CRITICAL | Low |
| 4 | C5 | Privacy note and docs make inaccurate claims (R45) | CRITICAL | Low |
| 5 | H1 | Backend text not localised (R11, R13) | HIGH | Medium |
| 6 | H2 | Advisor robustness / "GenAI" claim for the judges' 15 live scenarios (R20, R52) | HIGH | Medium |
| 7 | H3 | Decisions and withdrawal after activation corrupt order state (R31, R35) | HIGH | Low |
| 8 | H6 | Single monthly price rule (R24) | HIGH | Low |
| 9 | H5 | Unauthenticated reset/advance/image routes (R45) | HIGH | Low |
| 10 | H4 | Live "leads the advisor could not close" (R38) | HIGH (stretch named in brief) | Medium |
| 11 | C2 | Demo video (R41), recorded last so it shows the fixed product | CRITICAL | Low–Medium |

Medium and low items are listed in the remediation plan.

## 10. Final verdict

The prototype is technically strong: correct data-grounded business logic, honest simulation labels, a KYC engine that catches every planted problem found by inspection, and analytics that reconcile to the last rupee. As it stands, it is **not ready for judging**:

- two mandatory deliverables don't exist;
- the core "preferred language" promise breaks as soon as a Hindi user reads a plan reason;
- the advisor will look scripted under the judges' 15 unseen scenarios;
- a judge clicking around KYC could trigger the document-deletion bug;
- the privacy note overstates two protections.

None of these needs a redesign. With the Phase A–D work (about 1–2 days), the solution can credibly be called substantially compliant and compete for the top three.
