# SYNC Business — Intelligent MSME Onboarding Platform

**From business discovery to digital activation in one seamless journey.**
SYNC Hackathon 2026 · Enterprise Track A · Project Udyam Digital.

> Prototype only. Accel Telecom / Accel Business are fictional operators from the case study. All businesses, people, identifiers and documents are synthetic. No real GST, Udyam, DigiLocker, e-sign, payment or telecom system is connected.

A small-business owner chats with an advisor in English, Hindi or Tamil, gets three plans built only from the real product catalogue (each product with a reason), edits a transparent quote, checks out, gives DPDP-style consent, uploads four KYC documents that are OCR'd and checked against mock registries in seconds, and tracks installation with an expected date for every step. Sales, KYC and partner teams get an Intelligence Console with the true funnel, drop-off levers, a KYC exception queue, a callback queue and an explainable lead-priority score.

## What is in the repo

```
backend/            FastAPI app (Python 3.12)
  app/data.py         loads the supplied CSVs (single source of truth)
  app/advisor.py      slot-filling conversation, EN/HI/TA, optional LLM fallback
  app/recommend.py    eligibility, dependencies, quantities, Essential/Growth/Advanced
  app/quote.py        catalogue price x quantity, no discounts
  app/orders.py       quotes, checkout, order lifecycle, expected dates
  app/kyc/            OCR (Tesseract), extraction, GSTIN/Udyam validation, verification, consent, retention
  app/analytics.py    funnel, segments, drop levers, compliance audit, lead score + backtest
  app/scenarios.py    5 reproducible demo journeys from real dataset records
  tests/              45 pytest tests (real OCR on the specimen images)
frontend/           React 19 + TypeScript + Vite + Tailwind 4 (+ recharts, lucide)
  src/i18n/           en.ts, hi.ts, ta.ts (add a language = add a file)
  src/pages/          Landing, Advisor, Plans, Quote, Checkout, Consent, Kyc, Track, Console
docs/               audit, data/catalogue/KYC analysis, decisions, architecture, business case, privacy note, demo script
submission/         SYNC_Business_Case.pptx (10 slides) + generator script
6ad9d4887d445_airtel_sync/, YTL_TrackA_Udyam_Digital_Data/, *.zip   supplied materials, untouched
```

## Prerequisites

- Python 3.11+ and Node 20+
- Tesseract OCR: `brew install tesseract` (macOS) or `sudo apt install tesseract-ocr` (Linux)

## Install

```bash
pip install -r backend/requirements.txt
```

```bash
npm --prefix frontend install
```

## Run (one port)

```bash
npm --prefix frontend run build
```

```bash
python3 -m uvicorn app.main:app --app-dir backend --port 8000
```

Open http://localhost:8000 (customer app), http://localhost:8000/console (Intelligence Console), http://localhost:8000/docs (API).

### Frontend development mode

Run the backend as above, then:

```bash
npm --prefix frontend run dev
```

Vite serves http://localhost:5173 and proxies `/api` to port 8000.

## Configuration

Everything is optional; see `.env.example`. Export variables before starting the backend, for example:

```bash
export ANTHROPIC_API_KEY=sk-...   # optional: nicer phrasing + free-text fallback
```

| Variable | Default | Purpose |
|---|---|---|
| `ANTHROPIC_API_KEY` | unset | Optional LLM. Never chooses products or prices |
| `SYNC_LLM_MODEL` | `claude-haiku-5-5` | Model id for the optional LLM |
| `SYNC_CONSOLE_KEY` | `demo-console` | Header key for console endpoints |
| `SYNC_DEMO_MODE` | `1` | `0` makes specimen-watermarked documents fail KYC |
| `SYNC_REFERENCE_DATE` | `2026-07-15` | "Today" for document date checks |

## Synthetic data

The backend reads the CSVs in `YTL_TrackA_Udyam_Digital_Data/` at start-up (pandas, cached in memory) and seeds a read-only `products` table in SQLite. No record is copied into code. KYC specimens are read from `kyc_documents/` and copied into a case only when a user picks "Use specimen documents". Runtime state lives in `backend/var/` (git-ignored); **Console → Reset demo data** (or `POST /api/demo/reset`) wipes it.

## Demo scenarios

Landing page → *Demo businesses* → *Run this journey* → *Play demo conversation*.

| Scenario | Dataset lead | KYC pack | What it shows |
|---|---|---|---|
| Neighbourhood salon (micro) | L00115 | K06 | Budget-aware Essential plan; KYC catches an altered GSTIN digit |
| Dental clinic (professional) | L01287 | K02 | Full happy path; tilted scan straightened automatically |
| 11-store electronics chain (multi-site) | L03558 | K12 | Per-site quantities, failover, SD-WAN, CCTV |
| Furniture workshop (manufacturer) | L03571 | K03 | Leased line, IoT, 21-day install drives the date |
| Travel agency (KYC exception) | L00045 | K01 | Cancelled GSTIN blocks GST products in the advisor; KYC action required; reviewer approval in console |

Before recording, run `python3 backend/seed_demo.py` (server running) to reset and pre-load console exceptions; see `docs/THREE_MINUTE_DEMO_SCRIPT.md`.

Any pack K01–K12 can be loaded on the KYC screen. See `docs/KYC_DOCUMENT_ANALYSIS.md` for what each contains.

## Tests

```bash
python3 -m pytest backend/tests -q
```

Covers catalogue loading, pricing, every eligibility rule, dependencies, quantities, GSTIN format/checksum/registry status, Udyam lookups, OCR extraction on the specimens, watermark detection, deskew, blur → manual review, missing documents, altered GSTIN, name/address mismatch, 90-day boundary, signatory mismatch, consent gating and withdrawal, upload validation, checkout, expected dates, status progression, KYC gating, reviewer decisions, handoffs, console auth and the analytics baseline (funnel 5,000 → 368, blended CAC ₹15,053, GSTIN 9.6% vs 2.0%).

## Current limitations

- Mock registries only; no real GSTN/Udyam/DigiLocker/e-sign/payment integration (adapter boundaries are documented in `docs/SOLUTION_ARCHITECTURE.md`).
- Advisor understanding is rule-based; unusual phrasing falls back to tap-able options (or the optional LLM).
- OCR is tuned to the specimen layout; real-world photos need a stronger model and more templates.
- Serviceability and installation steps are simulated (demo controls on the tracker).
- Console auth is a shared key; no per-partner data partitioning yet.
- SQLite single-node persistence; Hindi and Tamil strings were written and reviewed by hand but should be checked by native-speaking reviewers before a pilot.
- Lead score is a transparent baseline (AUC ≈ 0.69 on a time split of synthetic data), not a validated predictive model.
