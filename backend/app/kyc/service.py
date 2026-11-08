"""KYC case lifecycle: consent -> uploads -> verification -> (manual review) -> decision. Also retention purge."""
from __future__ import annotations

import shutil
from datetime import datetime, timedelta, timezone

from .. import db
from ..config import ALLOWED_UPLOAD_TYPES, DOCUMENT_RETENTION_DAYS, KYC_SPECIMEN_DIR, MAX_UPLOAD_BYTES, UPLOAD_DIR
from .pipeline import DOC_LABELS, REQUIRED_DOCS, analyse_document, verify
from .validators import mask_id

NOTICE_VERSION = "2026-07-v1"
PURPOSES = {
    "kyc_verification": {"required": True},
    "service_delivery": {"required": True},
    "partner_installation": {"required": False},
    "product_updates": {"required": False},
}
MASK_FIELDS = {"gstin", "udyam_number", "id_number", "consumer_no"}


class KycError(ValueError):
    pass


# ------------------------------------------------------------------ consent

def record_consent(order: dict, choices: dict[str, bool], language: str) -> dict:
    missing = [p for p, meta in PURPOSES.items() if meta["required"] and not choices.get(p)]
    if missing:
        raise KycError("KYC cannot start without consent for: " + ", ".join(missing))
    ts = db.now()
    for purpose in PURPOSES:
        db.insert("consent_records", {"id": db.new_id("CN"), "customer_id": order["customer_id"], "order_id": order["id"],
                                      "purpose": purpose, "granted": int(bool(choices.get(purpose))),
                                      "notice_version": NOTICE_VERSION, "language": language, "granted_at": ts,
                                      "withdrawn_at": None})
    case = db.one("SELECT * FROM kyc_cases WHERE order_id=?", (order["id"],))
    if not case:
        cid = db.new_id("K")
        db.insert("kyc_cases", {"id": cid, "order_id": order["id"], "customer_id": order["customer_id"],
                                "status": "collecting", "created_at": ts, "updated_at": ts})
        db.execute("UPDATE orders SET kyc_case_id=? WHERE id=?", (cid, order["id"]))
        case = db.one("SELECT * FROM kyc_cases WHERE id=?", (cid,))
    db.audit("customer", "consent_granted", "order", order["id"], ",".join(p for p, v in choices.items() if v))
    return {"case_id": case["id"], "consents": consents(order["id"])}


def consents(order_id: str) -> list[dict]:
    return db.query("SELECT purpose, granted, notice_version, granted_at, withdrawn_at FROM consent_records "
                    "WHERE order_id=? ORDER BY granted_at", (order_id,))


def withdraw_consent(order: dict) -> dict:
    """Withdrawing KYC consent stops processing and deletes uploaded documents immediately."""
    db.execute("UPDATE consent_records SET withdrawn_at=? WHERE order_id=? AND withdrawn_at IS NULL", (db.now(), order["id"]))
    case = db.one("SELECT * FROM kyc_cases WHERE order_id=?", (order["id"],))
    purged = 0
    if case:
        purged = _purge_case_files(case["id"])
        db.update("kyc_cases", case["id"], {"status": "withdrawn", "updated_at": db.now()})
    db.update("orders", order["id"], {"delay_reason": "Consent withdrawn by customer; order on hold.", "updated_at": db.now()})
    db.audit("customer", "consent_withdrawn", "order", order["id"], f"documents purged: {purged}")
    return {"withdrawn": True, "documents_deleted": purged}


def _active_consent(order_id: str) -> bool:
    row = db.one("SELECT granted, withdrawn_at FROM consent_records WHERE order_id=? AND purpose='kyc_verification' "
                 "ORDER BY granted_at DESC LIMIT 1", (order_id,))
    return bool(row and row["granted"] and not row["withdrawn_at"])


# ------------------------------------------------------------------ uploads

def _case(case_id: str) -> dict:
    case = db.one("SELECT * FROM kyc_cases WHERE id=?", (case_id,))
    if not case:
        raise KycError("KYC case not found.")
    if not _active_consent(case["order_id"]):
        raise KycError("Consent for KYC verification is missing or withdrawn.")
    order = db.one("SELECT stage FROM orders WHERE id=?", (case["order_id"],))
    if order and order["stage"] != "kyc":
        raise KycError("KYC is already complete for this order; documents can no longer be changed.")
    return case


def upload(case_id: str, doc_type: str, data: bytes, content_type: str | None) -> dict:
    case = _case(case_id)
    if doc_type not in REQUIRED_DOCS:
        raise KycError("Unknown document type.")
    if len(data) > MAX_UPLOAD_BYTES:
        raise KycError("File is larger than 8 MB.")
    if not any(data.startswith(magic) for magic in ALLOWED_UPLOAD_TYPES.values()):
        raise KycError("Only PNG or JPEG images are accepted.")
    result = analyse_document(data, doc_type)
    folder = UPLOAD_DIR / case["id"]
    folder.mkdir(parents=True, exist_ok=True)
    doc_id = db.new_id("D")
    path = folder / f"{doc_id}.bin"  # never the user's filename
    path.write_bytes(data)
    db.execute("DELETE FROM kyc_documents WHERE case_id=? AND declared_type=?", (case_id, doc_type))
    purge_after = (datetime.now(timezone.utc) + timedelta(days=DOCUMENT_RETENTION_DAYS)).isoformat(timespec="seconds")
    db.insert("kyc_documents", {"id": doc_id, "case_id": case_id, "declared_type": doc_type,
                                "detected_type": result["detected_type"], "stored_path": str(path), "sha256": result["sha256"],
                                "size_bytes": len(data), "ocr_confidence": result["ocr_confidence"],
                                "fields_json": db.jdump(result["fields"]),
                                "quality_json": db.jdump({**result["quality"], "specimen": result["specimen"]}),
                                "created_at": db.now(), "purge_after": purge_after})
    db.update("kyc_cases", case_id, {"status": "collecting", "updated_at": db.now()})
    return public_document(db.one("SELECT * FROM kyc_documents WHERE id=?", (doc_id,)))


def specimen_packs() -> list[dict]:
    packs: dict[str, list[str]] = {}
    for f in sorted(KYC_SPECIMEN_DIR.glob("K*_*.png")):
        k, t = f.stem.split("_", 1)
        packs.setdefault(k, []).append(t)
    return [{"applicant": k, "documents": v} for k, v in packs.items()]


def load_specimen(case_id: str, applicant: str) -> list[dict]:
    if not applicant.isalnum() or len(applicant) > 4:
        raise KycError("Unknown specimen applicant.")
    out = []
    db.execute("DELETE FROM kyc_documents WHERE case_id=?", (case_id,))
    for t in REQUIRED_DOCS:
        f = KYC_SPECIMEN_DIR / f"{applicant}_{t}.png"
        if f.exists():
            out.append(upload(case_id, t, f.read_bytes(), "image/png"))
    if not out:
        raise KycError("Unknown specimen applicant.")
    return out


def public_document(row: dict) -> dict:
    fields = db.jload(row["fields_json"], {})
    return {"id": row["id"], "declared_type": row["declared_type"], "label": DOC_LABELS[row["declared_type"]],
            "detected_type": row["detected_type"], "ocr_confidence": row["ocr_confidence"],
            "quality": db.jload(row["quality_json"], {}), "purge_after": row["purge_after"], "purged": bool(row["purged_at"]),
            "fields": {k: {"value": mask_id(v["value"]) if k in MASK_FIELDS else v["value"], "conf": v["conf"]}
                       for k, v in fields.items()}}


# ------------------------------------------------------------------ verification and decisions

def declared_for(order_id: str) -> dict:
    o = db.one("SELECT o.*, c.business_name, c.contact_name FROM orders o JOIN customers c ON c.id=o.customer_id WHERE o.id=?",
               (order_id,))
    q = db.one("SELECT profile_json FROM quotes WHERE id=?", (o["quote_id"],))
    prof = db.jload(q["profile_json"], {})
    return {"business_name": o["business_name"], "signatory_name": o["contact_name"],
            "gstin": prof.get("gstin"), "udyam_number": prof.get("udyam_number")}


def run_verification(case_id: str) -> dict:
    case = _case(case_id)
    rows = db.query("SELECT * FROM kyc_documents WHERE case_id=? AND purged_at IS NULL", (case_id,))
    docs = {}
    for r in rows:
        q = db.jload(r["quality_json"], {})
        docs[r["declared_type"]] = {"detected_type": r["detected_type"], "fields": db.jload(r["fields_json"], {}),
                                    "ocr_confidence": r["ocr_confidence"], "quality": q, "specimen": q.get("specimen", False)}
    result = verify(docs, declared_for(case["order_id"]))
    db.execute("DELETE FROM verification_results WHERE case_id=?", (case_id,))
    db.many("INSERT INTO verification_results (case_id, code, label, status, detail, source, created_at) VALUES (?,?,?,?,?,?,?)",
            [(case_id, c["code"], c["label"], c["status"], c["detail"], c["source"], db.now()) for c in result["checks"]])
    db.update("kyc_cases", case_id, {"status": result["status"], "summary_json": db.jdump(result), "updated_at": db.now()})
    _sync_order(case["order_id"], result["status"])
    db.audit("system", "kyc_verified", "kyc_case", case_id, result["status"])
    return get_case(case_id)


def _sync_order(order_id: str, status: str):
    from ..orders import _event, advance
    reasons = {"manual_review": "KYC documents are with a specialist for review.",
               "action_required": "Waiting for corrected KYC documents.",
               "rejected": "KYC was not approved. Our team will call you."}
    if status in ("passed_demo", "approved"):
        o = db.one("SELECT stage FROM orders WHERE id=?", (order_id,))
        _event(order_id, "kyc", "KYC passed demo verification." if status == "passed_demo" else "KYC approved by reviewer.")
        if o["stage"] == "kyc":
            advance(order_id, actor="system")
    else:
        db.update("orders", order_id, {"delay_reason": reasons[status], "updated_at": db.now()})
        _event(order_id, "kyc", reasons[status])


def decide(case_id: str, decision: str, reviewer: str, reason: str) -> dict:
    if decision not in ("approved", "rejected"):
        raise KycError("Decision must be approved or rejected.")
    if not reason.strip():
        raise KycError("A reason is required for every manual decision.")
    case = db.one("SELECT * FROM kyc_cases WHERE id=?", (case_id,))
    if not case:
        raise KycError("KYC case not found.")
    db.update("kyc_cases", case_id, {"status": decision, "decision": decision, "decision_reason": reason[:500],
                                     "reviewer": reviewer[:60], "updated_at": db.now()})
    _sync_order(case["order_id"], decision)
    db.audit(reviewer, f"kyc_{decision}", "kyc_case", case_id, reason[:200])
    return get_case(case_id)


def get_case(case_id: str) -> dict | None:
    case = db.one("SELECT * FROM kyc_cases WHERE id=?", (case_id,))
    if not case:
        return None
    case["summary"] = db.jload(case.pop("summary_json"), None)
    case["documents"] = [public_document(r) for r in db.query("SELECT * FROM kyc_documents WHERE case_id=?", (case_id,))]
    case["missing"] = [t for t in REQUIRED_DOCS if t not in {d["declared_type"] for d in case["documents"]}]
    return case


def exception_queue() -> list[dict]:
    rows = db.query("""SELECT k.id, k.status, k.updated_at, k.summary_json, o.order_no, c.business_name, c.city
                       FROM kyc_cases k JOIN orders o ON o.id=k.order_id JOIN customers c ON c.id=k.customer_id
                       ORDER BY CASE k.status WHEN 'manual_review' THEN 0 WHEN 'action_required' THEN 1 ELSE 2 END, k.updated_at DESC""")
    out = []
    for r in rows:
        s = db.jload(r.pop("summary_json"), None) or {}
        r["issues"] = [c for c in s.get("checks", []) if c["status"] in ("fail", "review")]
        out.append(r)
    return out


def _purge_case_files(case_id: str) -> int:
    n = 0
    for r in db.query("SELECT id, stored_path FROM kyc_documents WHERE case_id=? AND purged_at IS NULL", (case_id,)):
        try:
            if r["stored_path"]:
                from pathlib import Path
                Path(r["stored_path"]).unlink(missing_ok=True)
        finally:
            db.execute("UPDATE kyc_documents SET purged_at=?, stored_path=NULL, fields_json='{}' WHERE id=?", (db.now(), r["id"]))
            n += 1
    shutil.rmtree(UPLOAD_DIR / case_id, ignore_errors=True)
    return n


def purge_expired() -> int:
    """Delete document images past their retention date. Called on startup."""
    n = 0
    for r in db.query("SELECT DISTINCT case_id FROM kyc_documents WHERE purged_at IS NULL AND purge_after < ?", (db.now(),)):
        n += _purge_case_files(r["case_id"])
    return n
