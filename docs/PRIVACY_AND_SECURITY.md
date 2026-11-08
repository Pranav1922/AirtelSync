# Privacy and security note (one page)

**Scope.** SYNC Business prototype for the SYNC 2026 hackathon. All data is synthetic; KYC images are specimens marked "not a valid document". The design treats them as if they were real customer data, in line with the Digital Personal Data Protection Act, 2023 (DPDP). Items marked **(prod)** need production work and legal review.

**1. Consent first, per purpose.** Before any document is collected the owner sees what is collected, why, how it is used, who can see it, how long it is kept and how to withdraw — in English, Hindi or Tamil. Four purposes are recorded separately with timestamp, notice version and language: KYC verification (required), service setup and billing (required), sharing address with the local installation partner (optional), product updates (optional, off by default). The API refuses uploads without an active KYC consent.

**2. Purpose limitation and minimisation.** The advisor asks only what the recommendation needs (business type, city, size, sites, current internet, needs, GST yes/no, budget). Checkout asks only business name, signatory name and role. KYC reads only the fields needed for verification. Contact phone/email are not collected in the prototype. The lead score excludes language, names, contact role, state and city.

**3. Masking.** GSTIN, Udyam number, ID number and consumer number are masked (`27•••••••••D1ZP`) in API responses, the chat transcript shown to the user, the console and server logs (a logging filter rewrites any identifier pattern). Identifier lookups use POST bodies so numbers never appear in URLs or access logs. The optional LLM never receives identifiers.

**4. Document handling.** Uploads are accepted only as PNG/JPEG (checked by magic bytes, not extension), ≤ 8 MB, stored under a random server-side name in a per-case folder — never the user's filename. OCR runs locally (Tesseract); no image leaves the server. Images are deleted **30 days** after upload (purge on start-up) and **immediately** if consent is withdrawn; extracted fields are wiped with them. Verification results are kept with the contract record. **(prod)** encryption at rest with KMS, malware scanning, object storage with signed URLs, retention aligned with telecom KYC obligations after legal review.

**5. Honest verification.** Every check is labelled *Extracted*, *Mock registry* or *Demo rule*. The UI and API state that genuine external verification (GSTN, Udyam portal, DigiLocker, e-sign) was **not performed**. Specimen watermarks are detected and reported; in production mode (`SYNC_DEMO_MODE=0`) they fail. Uncertain results (blurred image, signatory mismatch, near-match names) go to a human reviewer; every manual approve/reject requires a written reason and is stored in an audit log with the reviewer name.

**6. Access control.** Customer endpoints expose only the customer's own order by its unguessable ID/number. Console endpoints require a key header (`SYNC_CONSOLE_KEY`). **(prod)** SSO, role-based access (sales, KYC desk, partner), partner-scoped data, OTP-verified customer sessions, rate limiting, TLS everywhere.

**7. Secrets and integrity.** No secrets in the repository; `.env.example` documents optional variables. Prices and eligibility are computed server-side and re-validated at checkout, so a tampered client cannot buy an ineligible or mis-priced bundle. Inputs are validated with Pydantic and length limits; SQL uses parameters only.

**8. Rights.** Withdrawal (one click in the tracker) deletes documents and pauses the order. **(prod)** access/correction/erasure requests, grievance officer contact, breach-notification runbook and a DPIA before launch.
