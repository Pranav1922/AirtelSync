# KYC specimen inventory and findings

Method: each of the 47 images was opened and viewed, its pixels measured (size, sharpness, watermark colour ratio), OCR'd with Tesseract after watermark removal, and every extracted value cross-checked against the mock registries and the matching lead in `smb_leads.csv`. Findings below were derived by inspection; no answer key was used. The same checks are automated in `backend/app/kyc/pipeline.py` and asserted in `backend/tests/test_kyc.py`.

**Every one of the 47 images is marked "SYNTHETIC SPECIMEN – NOT A VALID DOCUMENT"** (diagonal light-red watermark; footer "Fictional business, person and identifiers"). They are test material only. The product reports them as *specimen — accepted for demo validation only* and would reject them in production mode (`SYNC_DEMO_MODE=0`).

## Inventory

| Applicant | Business (matching lead) | GST | Udyam | Address | Signatory | Finding | Engine result |
|---|---|:-:|:-:|:-:|:-:|---|---|
| K01 | Vindhya Tours & Travels, Visakhapatnam (L00045) | ✓ | ✓ | ✓ | ✓ | GSTIN **Cancelled** in registry; Udyam number field **blank** | Action required |
| K02 | Harmony Dental Care, Kolkata (L01287) | ✓ *tilted ~7°* | ✓ | ✓ | ✓ | Skewed scan; content consistent | Deskewed, passed demo |
| K03 | Ganesh Woodcraft, Nagpur (L03571) | ✓ | ✓ | ✓ | ✓ | Clean | Passed demo |
| K04 | Saffron Dental Care LLP, Nagpur (L01014) | ✓ **blurred** | ✓ | ✓ | ✓ | GST certificate unreadable (sharpness 0.4 vs ~7) | Manual review |
| K05 | Balaji Realty LLP, Kochi (L04014) | ✓ | **✗ missing** | ✓ | ✓ | Only 3 of 4 documents (explains 47 = 48 − 1) | Action required |
| K06 | Saffron Unisex Salon, Jaipur (L00115) | ✓ | ✓ | ✓ | ✓ | Printed GSTIN `08YKZXS`**8**`189L1ZO`, registry `…`**5**`189…` → **checksum fails** (altered/mistyped) | Action required |
| K07 | Neelgiri Physio Clinic, Delhi (L03349) | ✓ | ✓ | ✓ | ✓ | Legal name "Neha Banerjee (Prop. **Shri** Physio Clinic)" vs trade name & registry "**Neelgiri** Physio Clinic" | Action required |
| K08 | Green Leaf Legal Associates, Vadodara (L03473) | ✓ | ✓ | ✓ | ✓ | Clean | Passed demo |
| K09 | Kaveri Insurance Advisors, Visakhapatnam (L04779) | ✓ | ✓ | ✓ | ✓ | Clean | Passed demo |
| K10 | Kaveri Stays LLP, Mumbai (L04525) | ✓ | ✓ | ✓ | ✓ | Signatory ID **Nisha Arora**; lead contact/owner **Fatima Menon** | Manual review (authorisation letter) |
| K11 | Trinity Bake House Pvt Ltd, Ludhiana (L03485) | ✓ | ✓ | ✓ | ✓ | Electricity bill dated **2025-10-31 = 257 days** before 2026-07-15 | Action required |
| K12 | Star Electronics, Visakhapatnam (L03558) | ✓ | ✓ | ✓ | ✓ | Clean | Passed demo |

Clean packs: K03, K08, K09, K12 (and K02 after deskew). Planted problems: K01, K04, K05, K06, K07, K10, K11.

## Pipeline behaviour worth knowing

- **Watermark removal**: real text is dark; the watermark is light red. Keeping only pixels with max(R,G,B) < 140 removes it and lifted OCR from unreliable to ~95% line confidence.
- **Deskew**: projection-profile search over ±12° (K02 needs 7°).
- **Blur detection**: second-difference sharpness < 2.0 → low-quality flag → manual review, never a guess.
- **Checksum-guided OCR repair**: Tesseract read K01 `37IHK…` as `37THK…` and K10 `27QHJ…` as `27QHI…`. Both fail the checksum. The engine tries single substitutions among visually confusable glyphs (I/T/J/1, O/0/D, S/5, B/8, Z/2, G/6) and accepts a fix only if exactly one candidate passes the checksum **and** exists in the registry; the fix is reported. K06's 5→8 change is not a confusable pair, so it is correctly *not* repaired and fails.
- Per-field OCR confidence is shown to the user and stored; GSTIN lines typically score lower (52-84%) than name lines (95%+), which is why the checksum, not confidence, decides validity.

## Dataset inconsistencies (logged as "info", not blocking)

- On all 10 readable Udyam certificates the **registration date differs** from `mock_udyam_registry.csv`, and four certificates print "Services" where the registry says "Trading". Because this affects every applicant equally, it is treated as generator noise: shown to reviewers, never used to block.
- GST "Date of liability" matches the registry `registration_date` on every certificate.

## Field mapping

| Document | Fields extracted |
|---|---|
| GST certificate | GSTIN, legal name, trade name, constitution, principal place of business (2-line wrap re-joined), date of liability, registration type |
| Udyam certificate | Udyam number, enterprise name, major activity, city, state, registration date |
| Address proof | Consumer no., billed to, supply address, bill date, units, amount |
| Signatory ID | Name, designation, business, ID no., valid till |
