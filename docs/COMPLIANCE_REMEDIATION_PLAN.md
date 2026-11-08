# Compliance remediation plan

Derived from `docs/FINAL_PROBLEM_STATEMENT_COMPLIANCE_AUDIT.md`. Requirement IDs (R##) and PDF pages refer to that matrix. Tasks are ordered by their impact on hackathon compliance and how feasible they are. Estimated total for phases A–D: about 1.5 working days.

## Phase A — Mandatory problem-statement requirements

### A1 · Create the code repository (C1)
- **Priority / requirement:** CRITICAL · R42 · p.4
- **Files:** repo root (`.gitignore` already exists)
- **Expected outcome:** a public or judge-shared GitHub repository containing code, docs, the deck, and the supplied data where licensing allows (the case calls the data synthetic; the original ZIPs are 7.7 MB).
- **Acceptance:** a fresh `git clone` + README commands run the app; no `.env`, `backend/var/`, `node_modules/` or `dist/` committed.
- **Test:** clone into a temp directory → `pip install -r backend/requirements.txt`, `npm --prefix frontend install && npm --prefix frontend run build`, start the server, open `/api/health`.

### A2 · Make the journey speak the owner's language end to end (H1)
- **Priority / requirement:** HIGH · R11, R13, R23 · p.3
- **Files:**
  - Backend: `backend/app/recommend.py` (reasons/notes/pitch), `quote.py` (explanation), `orders.py` (event notes, pending actions, delay reasons), `kyc/pipeline.py` (check labels/details, summary message), `kyc/service.py` (delay reasons)
  - Frontend: `frontend/src/i18n/{en,hi,ta}.ts`; pages `Plans.tsx`, `Quote.tsx`, `Kyc.tsx`, `Track.tsx`
- **Expected outcome:** the backend returns `{code, params}` next to each English string. The frontend renders `t(code, params)` and falls back to the English text. Business-type and city chips get labels.
- **Acceptance:** in a Hindi or Tamil session, no English sentence appears on Plans, Quote, KYC results or Tracker. Product names, IDs and identifiers stay as they are.
- **Test:** new pytest asserting every reason/check carries a `code`. A script checks every code exists in `en.ts`, `hi.ts` and `ta.ts`. Manual Hindi pass through the clinic journey.

### A3 · Adopt and state a single monthly price (H6)
- **Priority / requirement:** HIGH · R24 · p.3
- **Files:** `backend/app/quote.py`, `frontend/src/pages/{Plans,Quote,Checkout,Track}.tsx`, `docs/PRODUCT_DECISIONS.md` #6, deck slide 5/8
- **Expected outcome:** one headline price per bundle (recommended rule: catalogue minimum, "locked once KYC passes"). The range moves into "How this price is calculated".
- **Acceptance:** every screen shows one monthly figure. The explanation states the rule and the catalogue ceiling. No discount appears.
- **Test:** extend `test_price_is_catalogue_price_times_quantity…` with a `monthly_price` field equal to `monthly_min`.

### A4 · Consent defaults and wording (C4)
- **Priority / requirement:** CRITICAL · R15, R34 · p.3
- **Files:** `frontend/src/pages/Consent.tsx:19`; `frontend/src/i18n/*.ts` `consent.keep.d`
- **Expected outcome:** every optional purpose starts unticked. The retention text says "30 days after upload" (matching `service.py:102`), or the code changes to "after verification" — pick one.
- **Acceptance:** a fresh consent screen has only empty boxes; text and code agree.
- **Test:** API test — consent with only the required purposes records `partner_installation=0`. Visual check.

## Phase B — Core functional gaps

### B1 · Fix the KYC lifecycle integrity bugs (C3)
- **Priority / requirement:** CRITICAL · R31 · p.3
- **Files:** `backend/app/kyc/service.py` (`load_specimen`, `upload`, `_purge_case_files`)
- **Expected outcome:**
  - `load_specimen` calls `_case()` (consent + lock check) **before** deleting anything.
  - Any replaced or wiped document row also has its file deleted.
  - Optional: reject the same SHA-256 uploaded under two document types.
- **Acceptance:** after KYC passes, a specimen-load attempt returns 400 **and** all 4 document rows and files remain.
- **Test:** extend `test_full_happy_journey_reaches_activation` to count `documents` before and after the refused call. New test: replacing a document leaves exactly one file in the case folder.

### B2 · Freeze decisions and withdrawal after KYC is closed (H3)
- **Priority / requirement:** HIGH · R31, R35 · p.3
- **Files:** `backend/app/kyc/service.py` (`decide`, `withdraw_consent`), `frontend/src/pages/Track.tsx` (withdraw link)
- **Expected outcome:**
  - `decide` is allowed only when the order stage is `kyc` and the case is `manual_review`/`action_required`.
  - Withdrawal after activation deletes the documents (still required) but does not put a live service "on hold"; it records the event instead.
  - The link label changes after activation ("Delete my KYC documents").
- **Acceptance:** a reviewer reject on an activated order returns 400 and the delay reason stays empty.
- **Test:** new pytest mirroring the live audit failure.

### B3 · Advisor robustness and the GenAI claim (H2)
- **Priority / requirement:** HIGH · R20, R52 · p.3, p.4
- **Files:** `backend/app/advisor.py`, `backend/app/llm.py`, `frontend/src/pages/Advisor.tsx`, `README.md`
- **Expected outcome:**
  1. Number words (one–hundred, Hindi एक–दस), activity verbs ("we make / manufacture / sell / run"), "I don't know" for every slot, "same as before" handling.
  2. Run the LLM fallback once with a real key and fix whatever breaks. Mask identifiers before sending.
  3. When an answer overwrites an earlier one, the advisor confirms ("Updated staff from 12 to 30").
  4. The UI states whether AI phrasing is on.
- **Acceptance:**
  - A 20-phrase regression set (5 per segment, mixed EN/HI/TA) reaches a recommendation with ≤ 1 repeated question each.
  - With a key, `llm.explain` returns a summary and `extract_slots` handles "we make furniture".
- **Test:** new parametrised `tests/test_advisor_phrases.py`; one manual run with `ANTHROPIC_API_KEY` set.

### B4 · Live "leads the advisor could not close" (H4)
- **Priority / requirement:** HIGH (named stretch) · R38 · p.3
- **Files:** `backend/app/main.py` (new `GET /api/console/unconverted`), `frontend/src/pages/Console.tsx` (new tab or section)
- **Expected outcome:** lists live advisor sessions with no quote, and draft quotes not checked out, with the last step, profile summary, time idle, open callback (if any), and the lead score computed from the profile.
- **Acceptance:** abandoning a journey at Plans shows it in the console within one refresh.
- **Test:** API test — create a session plus a quote without checkout → it appears.

### B5 · Make partner involvement visible (R18)
- **Priority / requirement:** MEDIUM · R18 · p.3
- **Files:** `backend/app/orders.py` (`list_orders` select `partner_code`), `Console.tsx` (Orders column + per-partner count), `Console.tsx` handoff assign (input for the assignee name)
- **Acceptance:** an order placed with code `CP-NAG-014` shows that code in the console; a handoff can be assigned to a typed name.
- **Test:** extend `test_delay_and_handoff`.

## Phase C — Technical quality and security

| Task | Pri | Req | Files | Acceptance / test |
|---|---|---|---|---|
| C1 Gate `POST /api/demo/reset` with the console key; keep `/advance` but require the console key or `SYNC_DEMO_MODE=1` | HIGH | R45 | `backend/app/main.py`, `Console.tsx`, `seed_demo.py`, `Track.tsx` demo controls | Reset without the key → 401; tests updated |
| C2 Longer order numbers (≥ 10 chars) or drop "unguessable" from the docs | HIGH | R45 | `orders.py:76`, `PRIVACY_AND_SECURITY.md` | Regex test on order format |
| C3 Mask identifiers before any LLM call; store advisor transcripts masked | HIGH | R45 | `advisor.py`, `llm.py`, `main.py` (`messages_json`) | Unit test: a GSTIN in the message never reaches `llm.complete` (monkeypatch) |
| C4 Serve the correct image media type (JPEG/PNG from magic bytes) | LOW | R28 | `main.py` `doc_image` | JPEG upload renders |
| C5 Console "Advance" shows API errors instead of swallowing them | LOW | R35 | `Console.tsx:313` | Error toast on KYC-gated order |
| C6 Don't display a default employee count before it is asked | LOW | R21 | `recommend.public_profile` / `ProfileCard` | Profile card empty until answered |
| C7 Dependency must be satisfied by an *eligible* product (clearer error) | LOW | R25 | `recommend.validate_bundle` | Test with P09 + ineligible P03 → dependency error too |
| C8 Periodic retention purge (hourly background task) | LOW | R34 | `main.py` lifespan | Unit test with `purge_after` in the past |
| C9 Pin dependency versions (`pip freeze` subset, `package-lock.json` committed) | LOW | R40 | `backend/requirements.txt`, `frontend/package-lock.json` | Clean install reproduces the build |
| C10 Tests for consent defaults, decisions after activation, lock-bypass deletion | MEDIUM | R31 | `backend/tests/` | Suite green |

## Phase D — Submission and demo readiness

| Task | Pri | Req | Files | Acceptance / test |
|---|---|---|---|---|
| D1 Correct the privacy note: order IDs, LLM data flow, retention wording, unauthenticated demo routes (or fix them via C1–C3 first); export to a one-page PDF | CRITICAL | R45 | `docs/PRIVACY_AND_SECURITY.md`, `submission/` | Every sentence traceable to code; PDF is 1 page |
| D2 Export the architecture diagram as PNG/PDF (components + data flow) | MEDIUM | R43 | `docs/SOLUTION_ARCHITECTURE.md`, `submission/architecture.png` | Opens without a Mermaid renderer |
| D3 Add contract length per segment bundle to the business case and slide 3 | MEDIUM | R12 | `docs/BUSINESS_CASE.md` §4, `submission/build_deck.js` | Deck validated; slide text shows months |
| D4 Replace "on one bill" claims with wording the prototype supports | MEDIUM | R07 | `backend/app/recommend.py`, deck slide 5 | grep "one bill" shows only labelled proposals |
| D5 Re-run the full test suite + live audit script; record the video per `THREE_MINUTE_DEMO_SCRIPT.md` (after A2, B1–B3) | CRITICAL | R41 | `docs/THREE_MINUTE_DEMO_SCRIPT.md` | Video ≤ 3:00, 1080p, shows the disclaimer and no defects |
| D6 Update README limitations and the audit statistics after the fixes | LOW | — | `README.md`, this plan | Statements match behaviour |

## Phase E — Optional differentiators (only after A–D)

| Task | Req | Note |
|---|---|---|
| E1 WhatsApp-style front end reusing `/api/advisor/*` (simulated chat skin or Twilio sandbox) | R37 (p.3, stretch) | Highest-value optional item; reuses the backend unchanged |
| E2 Voice input via the browser Web Speech API (hi-IN, ta-IN, en-IN) feeding the same text endpoint | R36 (p.3, stretch) | Small effort; works offline in Chrome |
| E3 Add Marathi, Kannada, Telugu, Gujarati UI files (top dataset languages after Hindi/English) | R11 | Only after A2 makes all text translatable |
| E4 DigiLocker / e-sign adapter interfaces with a clearly labelled stub | R57 | Documentation-level value only; never imply a live connection |
| E5 Compute landing-page stats from `/api/console/overview` (public subset) | R53 | Removes the last hard-coded figures |
