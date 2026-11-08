# SYNC Business – solution architecture

*From business discovery to digital activation in one seamless journey.*

## 1. System context

```mermaid
flowchart LR
  owner([MSME owner<br/>phone, EN / HI / TA]) --> web[SYNC customer app<br/>React + Vite]
  staff([Accel sales, KYC desk,<br/>channel partners]) --> console[SYNC Intelligence Console]
  web --> api[SYNC API<br/>FastAPI]
  console --> api
  api --> db[(SQLite<br/>transactions, consent, audit)]
  api --> csv[(Supplied synthetic CSVs<br/>catalogue · leads · registries)]
  api --> ocr[Local Tesseract OCR]
  api -. optional .-> llm[LLM API<br/>phrasing only]
  api -. future adapters .-> ext[GSTN · Udyam · DigiLocker · e-sign · billing · field-ops<br/><i>not connected in prototype</i>]
```

## 2. Components

```mermaid
flowchart TB
  subgraph Frontend["frontend/src"]
    L[Landing + demo scenarios] --> A[Advisor chat]
    A --> P[Plans: Essential / Growth / Advanced]
    P --> Q[Quote configurator]
    Q --> C[Checkout]
    C --> CN[Consent]
    CN --> K[Smart KYC]
    K --> T[Order tracker]
    H[Talk to a person] -.-> any((any step))
    CON[Intelligence Console: analytics · lead priority · KYC queue · orders · callbacks]
    I18N[i18n: en.ts · hi.ts · ta.ts]
  end
  subgraph Backend["backend/app"]
    MAIN[main.py · REST API · log masking · console auth]
    ADV[advisor.py · slot-filling NLU EN/HI/TA]
    REC[recommend.py · eligibility · dependencies · quantities · explanations]
    QT[quote.py · catalogue x quantity pricing]
    ORD[orders.py · quotes · checkout · lifecycle]
    KYCS[kyc/service.py · consent · uploads · decisions · retention]
    PIPE[kyc/pipeline.py · type detection · field extraction · cross-checks]
    OCR[kyc/ocr.py · quality · watermark removal · deskew · Tesseract TSV]
    VAL[kyc/validators.py · GSTIN checksum · registry lookups · masking]
    AN[analytics.py · funnel · segments · drop levers · lead score]
    LLM[llm.py · optional]
    DATA[data.py · CSV loaders]
    DB[db.py · schema]
  end
  MAIN --> ADV & REC & QT & ORD & KYCS & AN
  ADV --> LLM
  REC --> DATA & VAL
  KYCS --> PIPE --> OCR & VAL
  ORD --> REC & QT & DB
  AN --> DATA
```

## 3. Main data flow

```mermaid
sequenceDiagram
  actor O as Owner
  participant UI as Customer app
  participant API as SYNC API
  participant R as Rec. engine
  participant K as KYC pipeline
  participant DB as SQLite
  O->>UI: "Dental clinic in Kolkata, 5 staff"
  UI->>API: POST /advisor/sessions/{id}/messages
  API->>API: extract slots (rules, optional LLM fallback)
  API-->>UI: profile so far + next question
  O->>UI: types GSTIN
  API->>API: checksum + mock GSTIN registry status
  UI->>API: GET /advisor/sessions/{id}/recommendation
  API->>R: profile
  R-->>API: 3 bundles of real product IDs, reasons, prices, notes
  O->>UI: edits quote
  UI->>API: POST /quote/price (live validation)
  UI->>API: POST /quotes → POST /checkout
  API->>DB: quote, items, customer, order, events
  O->>UI: grants consent (2 required, 2 optional purposes)
  API->>DB: consent_records + kyc_case
  O->>UI: uploads 4 images
  API->>K: OCR + extract (per file)
  UI->>API: POST /kyc/{case}/verify
  K-->>API: checks with status + source
  alt all pass
    API->>DB: order → serviceability
  else review / action required
    API->>DB: delay reason, console queue
  end
  O->>UI: tracks order (expected date per step)
```

## 4. API surface

| Area | Endpoints |
|---|---|
| Meta | `GET /api/health`, `GET /api/meta`, `GET /api/catalogue`, `GET /api/scenarios`, `POST /api/demo/reset` |
| Advisor | `POST /api/advisor/sessions`, `GET /api/advisor/sessions/{id}`, `POST …/{id}/messages`, `PUT …/{id}/profile`, `GET …/{id}/recommendation`, `POST /api/recommend` |
| Quote | `POST /api/quote/price` (live, validates), `POST /api/eligibility`, `POST /api/quotes`, `GET /api/quotes/{id}` |
| Order | `POST /api/checkout`, `GET /api/orders/{id or number}`, `POST /api/orders/{id}/advance` (demo) |
| Consent | `GET /api/consent/notice`, `POST /api/orders/{id}/consent`, `POST /api/orders/{id}/consent/withdraw` |
| KYC | `GET /api/kyc/specimens`, `POST /api/kyc/{case}/documents` (multipart), `POST /api/kyc/{case}/specimen`, `POST /api/kyc/{case}/verify`, `GET /api/kyc/{case}`, `GET …/documents/{doc}/image` |
| Lookups | `POST /api/lookup/gstin`, `POST /api/lookup/udyam` (POST so identifiers never appear in URLs or access logs) |
| Help | `POST /api/handoff` |
| Console (header `X-Console-Key`) | `GET /api/console/overview`, `/leads`, `/live`, `/kyc`, `POST /api/console/kyc/{case}/decision`, `GET /api/console/orders`, `GET/PATCH /api/console/handoffs` |

Interactive docs: `http://localhost:8000/docs`.

## 5. Database

```mermaid
erDiagram
  customers ||--o{ advisor_sessions : has
  advisor_sessions ||--o{ quotes : produces
  quotes ||--|{ quote_items : contains
  products ||--o{ quote_items : priced_by
  quotes ||--o| orders : becomes
  customers ||--o{ orders : places
  orders ||--|{ order_events : logs
  orders ||--o{ consent_records : governed_by
  orders ||--o| kyc_cases : requires
  kyc_cases ||--o{ kyc_documents : holds
  kyc_cases ||--o{ verification_results : produces
  customers ||--o{ handoff_requests : raises
```

`products` is seeded from the CSV on start (read-only copy for referential integrity). `audit_log` records consent grants/withdrawals, KYC decisions (with reviewer and reason) and checkouts. `quote_items.quantity` has a CHECK constraint (1-500).

## 6. AI architecture

| Layer | Implementation | Can it change products or prices? |
|---|---|---|
| Understanding | Rule-based slot filling with EN/HI/TA keyword lexicons, number/city/GSTIN/Udyam/budget regexes; every message scanned for every slot | No |
| Optional LLM fallback | If no slot is found and `ANTHROPIC_API_KEY` is set: JSON extraction constrained to allowed values, then validated | No |
| Decision | `recommend.py`: hard eligibility → connectivity fallback chain per segment/level → stated needs → segment add-ons → dependency repair → pricing | Yes, deterministically |
| Evidence | Historical attach rates per segment shown in reasons (e.g. "41% of similar businesses that activated with us chose it" for backup in professional offices) | No |
| Explanation | Template summary; optional LLM rephrases the already-chosen bundle in the user's language using only the facts passed | No |
| Lead score | Naive-Bayes log-odds, time-split backtest, compliance guardrail, protected attributes excluded | Ranks leads only |

## 7. KYC architecture

```mermaid
flowchart LR
  up[Upload PNG/JPEG ≤ 8 MB<br/>magic-byte check] --> q[Quality: sharpness · skew · watermark ratio]
  q --> clean[Remove light-red watermark] --> desk[Deskew ±12°] --> tess[Tesseract TSV<br/>per-line confidence]
  tess --> type[Detect doc type] --> fields[Label/value extraction<br/>wrapped addresses joined]
  fields --> v{Cross-checks}
  v --> g[GSTIN format + checksum<br/>+ OCR repair] --> gr[Mock GSTIN registry status · names · address]
  v --> u[Udyam format → mock Udyam registry]
  v --> n[Business name across 4 docs + sign-up]
  v --> a[Bill address ↔ GST address · bill ≤ 90 days]
  v --> s[Signatory ↔ sign-up & proprietor · ID validity]
  gr & u & n & a & s --> d{Decision}
  d -->|all pass| pass[Passed demo validation]
  d -->|uncertain| rev[Manual review → Console]
  d -->|defect| act[Action required → customer]
```

## 8. Security boundaries

| Boundary | Prototype control | Production requirement |
|---|---|---|
| Browser ↔ API | Same origin in demo; CORS allow-list; Pydantic validation and length limits on every input | TLS, WAF, rate limiting, OTP-verified sessions |
| Console | Shared header key `SYNC_CONSOLE_KEY` | SSO + RBAC (sales, KYC desk, partner scopes), per-partner data partitioning |
| Uploads | Type by magic bytes, 8 MB cap, random server-side filename, never the user's filename | Malware scan, encryption at rest (KMS), object storage with signed URLs |
| Identifiers | Masked in API responses, chat bubbles and logs (log filter) | Tokenisation vault |
| External registries | Not called; local mock CSVs | Licensed GSP / Udyam / DigiLocker APIs behind an adapter with consent artefacts |
| LLM | Off by default; receives no identifiers (profile facts and product names only) | DPA with provider, India data residency, prompt logging policy |
