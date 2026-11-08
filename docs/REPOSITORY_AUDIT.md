# Repository audit

Audit performed before any application code was written. Nothing supplied was modified, moved or re-extracted.

## Starting state

| Path | What it is | Treatment |
|---|---|---|
| `6ad9d4887d445_airtel_sync.zip` | Original case pack archive | Preserved, untouched |
| `6ad9d4887d445_airtel_sync/Airtel_SYNC_Case.pdf` | 6-page case study | Read in full (pages 1-6, incl. appendices A1, A2) |
| `6ad9d4887d445_airtel_sync/Submission Template_Sync.pptx` | 2-slide template (16:9, 9144000x5143500 EMU) | Inspected; background images reused by reference in our own deck. Original never overwritten |
| `YTL_TrackA_Udyam_Digital_Data.zip` | Original dataset archive | Preserved, untouched |
| `YTL_TrackA_Udyam_Digital_Data/README.md` | Column guide and dataset rules | Read in full |
| `.../product_catalogue.csv` | 25 products | Loaded at runtime by `backend/app/data.py` |
| `.../smb_leads.csv` | 5,000 leads, 40 columns | Loaded at runtime |
| `.../mock_gstin_registry.csv` | 3,534 GSTINs | Backs the mock GSTIN lookup |
| `.../mock_udyam_registry.csv` | 2,723 Udyam numbers | Backs the mock Udyam lookup |
| `.../kyc_documents/` | 47 PNG specimens, 12 applicants | Read by local OCR; copied (never moved) into a case on demand |

There was no existing application code, git repository, build tooling or dependency manifest. The repository was therefore built from scratch with the stack recommended in the brief.

## Case requirements extracted from the PDF

- Fictional operator **Accel Telecom / Accel Business**; all figures synthetic. The prototype keeps a SYNC/hackathon identity and never presents itself as an Airtel service or a government service.
- Build challenge (must have): GenAI-style **advisor** grounded in the catalogue, **quote and checkout** with one transparent monthly price and toggles, **Smart KYC** with extraction, validation, mocked GSTIN/Udyam lookups and consent screen, **order tracker**.
- Stretch: voice/WhatsApp front end; **back-office view** of leads the advisor could not close; **propensity score**. We built the latter two.
- Key questions: segment prioritisation and bundle per segment; salesperson-free discovery in Hindi/regional languages; near-instant KYC under the **DPDP Act, 2023**; role of field force and channel partners; 3-5 success metrics with targets.
- Submission: prototype + 3-minute video, architecture diagram, business case of ≤ 10 slides, 1-page privacy & security note.
- Appendix A1 baselines: 7% activation, 17.6 days, 3 status chases, ₹15,000 blended CAC, ₹6,900 median bundle (~₹2,500 micro), 9.6% vs 2.0% activation with/without GSTIN.
- Appendix A2 segments: micro 55% (very high price sensitivity), professional 25% (medium), multi-site 15% (medium-low), manufacturers 5% (low).
- A separate judges-only pack exists (15 advisor scenarios, KYC answer key, planted signals). **It was not sought or used.** All anomalies in `KYC_DOCUMENT_ANALYSIS.md` were found by inspection.

## Dataset rules honoured in code

| Rule (README) | Where enforced |
|---|---|
| Reference date 2026-07-15 for date checks | `config.REFERENCE_DATE`, `kyc/pipeline.py` |
| Address proof ≤ 90 days old | `ADDRESS_PROOF_MAX_AGE_DAYS`, check `address_fresh` |
| GSTIN checksum is real; 4th PAN character `X` accepted | `kyc/validators.py` (`VALID_PAN_TYPES`) |
| Udyam district code `00` is fictional, accept it | `lookup_udyam` |
| GSTIN status Active / Cancelled / Suspended | `lookup_gstin`, eligibility (`gstin_ok`) |
| Collect minimum data, consent before KYC, mask identifiers, explain retention | `kyc/service.py`, `validators.mask_id`, log filter in `main.py`, `docs/PRIVACY_AND_SECURITY.md` |

## Tooling found on the machine

Python 3.12 with pandas, FastAPI, rapidfuzz, Pillow, pytest; Node 26 / npm; Tesseract 5 (`eng`). No paid API is required anywhere.
