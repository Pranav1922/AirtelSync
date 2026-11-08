"""Quotes, checkout, orders and the order lifecycle."""
from __future__ import annotations

from datetime import date, timedelta

from . import db
from .quote import price_items
from .recommend import resolve_profile, validate_bundle

STAGES = ["quote_accepted", "payment", "kyc", "serviceability", "installation_scheduled",
          "installation_in_progress", "activated"]
STAGE_LABEL = {"quote_accepted": "Quote accepted", "payment": "Payment", "kyc": "KYC verification",
               "serviceability": "Serviceability check", "installation_scheduled": "Installation scheduled",
               "installation_in_progress": "Installation in progress", "activated": "Activated"}
KYC_OK = {"passed_demo", "approved"}


class OrderError(ValueError):
    pass


def create_quote(profile: dict, items: dict[str, int], level: str | None, session_id: str | None) -> dict:
    p = resolve_profile(profile)
    errors = validate_bundle(items, p)
    if not items:
        errors.append({"product_id": None, "rule": "empty", "message": "Add at least one product."})
    pricing = price_items(items) if not errors else None
    if errors:
        return {"ok": False, "errors": errors}
    qid = db.new_id("Q")
    db.insert("quotes", {"id": qid, "session_id": session_id, "level": level, "profile_json": db.jdump(p),
                         "monthly_min": pricing["monthly_min"], "monthly_max": pricing["monthly_max"],
                         "setup_total": pricing["setup_total"], "commitment_months": pricing["longest_commitment_months"],
                         "install_days": pricing["install_days"], "status": "draft", "created_at": db.now()})
    db.many("INSERT INTO quote_items VALUES (?,?,?,?,?,?,?,?)",
            [(qid, li["product_id"], li["quantity"], li["unit_price_min"], li["unit_price_max"],
              li["setup"] // max(li["quantity"], 1), li["contract_months"], li["install_days"]) for li in pricing["lines"]])
    return {"ok": True, "quote_id": qid, "pricing": pricing}


def get_quote(qid: str) -> dict | None:
    q = db.one("SELECT * FROM quotes WHERE id=?", (qid,))
    if not q:
        return None
    q["profile"] = db.jload(q.pop("profile_json"), {})
    items = {r["product_id"]: r["quantity"] for r in db.query("SELECT * FROM quote_items WHERE quote_id=?", (qid,))}
    q["pricing"] = price_items(items)
    return q


def expected_dates(created: date, install_days: int) -> dict[str, str]:
    """Indicative plan: KYC +1 day, survey +2, install booked +3, activation after the slowest product installs."""
    offsets = {"quote_accepted": 0, "payment": 0, "kyc": 1, "serviceability": 2, "installation_scheduled": 3,
               "installation_in_progress": 3, "activated": 2 + max(install_days, 1)}
    return {s: (created + timedelta(days=d)).isoformat() for s, d in offsets.items()}


def checkout(quote_id: str, customer: dict, payment_mode: str, partner_code: str | None = None) -> dict:
    q = get_quote(quote_id)
    if not q:
        raise OrderError("Quote not found.")
    if q["status"] != "draft":
        raise OrderError("This quote has already been checked out.")
    errors = validate_bundle({li["product_id"]: li["quantity"] for li in q["pricing"]["lines"]}, resolve_profile(q["profile"]))
    if errors:
        raise OrderError(errors[0]["message"])
    if not (customer.get("business_name") or "").strip() or not (customer.get("contact_name") or "").strip():
        raise OrderError("Business name and authorised signatory name are required.")
    cid = db.new_id("C")
    p = q["profile"]
    db.insert("customers", {"id": cid, "business_name": customer["business_name"].strip()[:120], "segment": p.get("segment"),
                            "city": p.get("city"), "language": customer.get("language", "en"),
                            "contact_name": customer["contact_name"].strip()[:80], "contact_role": customer.get("contact_role"),
                            "source": customer.get("source", "Digital advisor"), "created_at": db.now()})
    oid = db.new_id("O")
    order_no = "SYNC-" + oid[-6:].upper()
    created = db.now()
    plan = expected_dates(date.fromisoformat(created[:10]), q["install_days"])
    setup = q["setup_total"]
    payment = "not_required" if setup == 0 else ("confirmed" if payment_mode == "pay_now" else "on_first_bill")
    db.insert("orders", {"id": oid, "order_no": order_no, "quote_id": quote_id, "customer_id": cid, "stage": "kyc",
                         "payment_status": payment, "expected_activation": plan["activated"],
                         "delay_reason": None, "partner_code": partner_code, "created_at": created, "updated_at": created})
    db.execute("UPDATE quotes SET status='accepted', customer_id=? WHERE id=?", (cid, quote_id))
    _event(oid, "quote_accepted", f"Quote accepted: Rs {q['monthly_min']:,}-{q['monthly_max']:,}/month.")
    note = {"confirmed": f"Setup fee Rs {setup:,} paid (simulated payment, no money moved).",
            "on_first_bill": f"Setup fee Rs {setup:,} will be added to the first bill.",
            "not_required": "No setup fee for this bundle."}[payment]
    _event(oid, "payment", note)
    db.audit("customer", "checkout", "order", oid, order_no)
    return get_order(oid)


def _event(oid: str, stage: str, note: str, actor: str = "system"):
    db.insert("order_events", {"order_id": oid, "stage": stage, "note": note, "actor": actor, "at": db.now()})


def get_order(key: str) -> dict | None:
    o = db.one("SELECT * FROM orders WHERE id=? OR order_no=?", (key, key.upper()))
    if not o:
        return None
    o["customer"] = db.one("SELECT id, business_name, contact_name, city, segment, language FROM customers WHERE id=?",
                           (o["customer_id"],))
    o["quote"] = get_quote(o["quote_id"])
    o["events"] = db.query("SELECT stage, note, actor, at FROM order_events WHERE order_id=? ORDER BY id", (o["id"],))
    kyc = db.one("SELECT id, status, decision, decision_reason FROM kyc_cases WHERE id=?", (o["kyc_case_id"],)) if o["kyc_case_id"] else None
    o["kyc"] = kyc
    created = date.fromisoformat(o["created_at"][:10])
    plan = expected_dates(created, o["quote"]["install_days"])
    plan["activated"] = o["expected_activation"]  # includes any delays recorded since checkout
    cur = STAGES.index(o["stage"])
    o["timeline"] = [{"stage": s, "label": STAGE_LABEL[s], "expected": plan[s],
                      "state": "done" if i < cur or o["stage"] == "activated" else "current" if i == cur else "upcoming"}
                     for i, s in enumerate(STAGES)]
    o["pending_actions"] = pending_actions(o)
    return o


def pending_actions(o: dict) -> list[str]:
    acts = []
    kyc = o.get("kyc")
    if o["stage"] == "kyc":
        if not kyc or kyc["status"] == "collecting":
            acts.append("Upload your KYC documents.")
        elif kyc["status"] == "action_required":
            acts.append("Fix the KYC items marked in red, or request a call back.")
        elif kyc["status"] == "manual_review":
            acts.append("No action needed: a KYC specialist is reviewing your documents.")
    if o["payment_status"] == "on_first_bill":
        acts.append("Setup fee will appear on your first bill.")
    return acts


def advance(oid: str, actor: str = "demo", delay_reason: str | None = None) -> dict:
    o = get_order(oid)
    if not o:
        raise OrderError("Order not found.")
    if o["stage"] == "activated":
        raise OrderError("Order is already active.")
    if delay_reason:
        db.update("orders", o["id"], {"delay_reason": delay_reason, "updated_at": db.now()})
        new_eta = (date.fromisoformat(o["expected_activation"]) + timedelta(days=2)).isoformat()
        db.update("orders", o["id"], {"expected_activation": new_eta})
        _event(o["id"], o["stage"], f"Delayed: {delay_reason}. New expected activation {new_eta}.", actor)
        return get_order(o["id"])
    if o["stage"] == "kyc" and (not o["kyc"] or o["kyc"]["status"] not in KYC_OK):
        raise OrderError("KYC must pass (or be approved by a reviewer) before the order can move on.")
    nxt = STAGES[STAGES.index(o["stage"]) + 1]
    notes = {"serviceability": "Site is serviceable for the selected products (simulated check).",
             "installation_scheduled": "Engineer visit booked.",
             "installation_in_progress": "Engineer on site installing equipment.",
             "activated": "All services are live. Welcome to Accel Business!"}
    db.update("orders", o["id"], {"stage": nxt, "delay_reason": None, "updated_at": db.now()})
    _event(o["id"], nxt, notes.get(nxt, STAGE_LABEL[nxt]), actor)
    return get_order(o["id"])


def list_orders() -> list[dict]:
    return db.query("""SELECT o.id, o.order_no, o.stage, o.payment_status, o.expected_activation, o.delay_reason,
                              o.created_at, c.business_name, c.city, c.segment, q.monthly_min, k.status AS kyc_status
                       FROM orders o JOIN customers c ON c.id=o.customer_id JOIN quotes q ON q.id=o.quote_id
                       LEFT JOIN kyc_cases k ON k.id=o.kyc_case_id ORDER BY o.created_at DESC""")
