"""SYNC Business API."""
from __future__ import annotations

import logging
import os
import re
from contextlib import asynccontextmanager

from fastapi import Depends, FastAPI, File, Form, Header, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from . import advisor, analytics, db, llm, orders, scenarios
from .config import CORS_ORIGINS, MAX_UPLOAD_BYTES, REFERENCE_DATE, ROOT
from .data import catalogue, city_tiers, leads
from .kyc import service as kyc
from .kyc.ocr import ocr_available
from .kyc.pipeline import DEMO_MODE
from .kyc.validators import lookup_gstin, lookup_udyam, mask_id
from .recommend import NEED_LABEL, product_eligibility, public_profile, recommend, resolve_profile, validate_bundle
from .quote import price_items


class MaskIdentifiers(logging.Filter):
    """Never let a GSTIN or Udyam number reach the logs in clear text."""
    PAT = re.compile(r"\b(\d{2}[A-Z]{5}\d{4}[A-Z][0-9A-Z]Z[0-9A-Z])\b|(UDYAM-[A-Z]{2}-\d{2}-\d{7})")

    def filter(self, record):
        sub = lambda v: self.PAT.sub(lambda m: mask_id(m.group(0)), v) if isinstance(v, str) else v  # noqa: E731
        record.msg = sub(record.msg)
        # Only rewrite string args: converting ints to str breaks "%d" placeholders.
        if isinstance(record.args, tuple):
            record.args = tuple(sub(a) for a in record.args)
        return True


for name in ("", "uvicorn", "uvicorn.access", "uvicorn.error", "sync"):
    logging.getLogger(name).addFilter(MaskIdentifiers())

@asynccontextmanager
async def lifespan(_app):
    db.conn()
    leads(); catalogue(); analytics.overview(); analytics.priority_queue()  # warm caches
    kyc.purge_expired()
    yield


app = FastAPI(title="SYNC Business API", version="1.0.0", lifespan=lifespan,
              description="Digital MSME acquisition and onboarding. Synthetic data, mock registries only.")
app.add_middleware(CORSMiddleware, allow_origins=CORS_ORIGINS, allow_methods=["*"], allow_headers=["*"])
CONSOLE_KEY = os.getenv("SYNC_CONSOLE_KEY", "demo-console")


def console_auth(x_console_key: str = Header(default="")):
    if x_console_key != CONSOLE_KEY:
        raise HTTPException(401, "Console key required.")


def _err(e: Exception):
    raise HTTPException(400, str(e))


# ------------------------------------------------------------------ meta

@app.get("/api/health")
def health():
    return {"status": "ok", "ocr": ocr_available(), "llm": llm.enabled(), "products": len(catalogue()),
            "leads": len(leads()), "reference_date": REFERENCE_DATE.isoformat()}


@app.get("/api/meta")
def meta():
    return {"languages": ["en", "hi", "ta"], "llm_enabled": llm.enabled(), "demo_mode": DEMO_MODE,
            "reference_date": REFERENCE_DATE.isoformat(), "needs": NEED_LABEL, "cities": city_tiers(),
            "chips": advisor.CHIPS, "external_verification": False}


@app.get("/api/catalogue")
def get_catalogue():
    return [p.public() for p in catalogue().values()]


@app.get("/api/scenarios")
def list_scenarios():
    return scenarios.all_public()


@app.post("/api/demo/reset")
def demo_reset():
    db.reset()
    return {"reset": True}


# ------------------------------------------------------------------ advisor

class SessionIn(BaseModel):
    language: str = "en"
    scenario: str | None = None


class MessageIn(BaseModel):
    text: str = Field(min_length=1, max_length=500)
    expecting: str | None = None


class ProfileIn(BaseModel):
    profile: dict


@app.post("/api/advisor/sessions")
def new_session(body: SessionIn):
    sid = db.new_id("S")
    db.insert("advisor_sessions", {"id": sid, "language": body.language, "scenario": body.scenario,
                                   "created_at": db.now(), "updated_at": db.now()})
    return {"session_id": sid, "next": "business_type", "chips": advisor.CHIPS["business_type"]}


def _session(sid: str) -> dict:
    s = db.one("SELECT * FROM advisor_sessions WHERE id=?", (sid,))
    if not s:
        raise HTTPException(404, "Session not found.")
    return s


@app.get("/api/advisor/sessions/{sid}")
def read_session(sid: str):
    profile = db.jload(_session(sid)["profile_json"], {})
    nxt = advisor.next_slot(profile)
    return {"profile": public_profile(resolve_profile(profile)) | {"needs_asked": profile.get("needs_asked", False)},
            "next": nxt, "chips": advisor.CHIPS.get(nxt, []), "done": nxt is None}


@app.post("/api/advisor/sessions/{sid}/messages")
def message(sid: str, body: MessageIn):
    s = _session(sid)
    profile = db.jload(s["profile_json"], {})
    msgs = db.jload(s["messages_json"], [])
    res = advisor.turn(profile, body.text, body.expecting, s["language"])
    msgs.append({"role": "user", "text": body.text, "at": db.now()})
    msgs.append({"role": "advisor", "next": res["next"], "extracted": list(res["extracted"]), "at": db.now()})
    db.update("advisor_sessions", sid, {"profile_json": db.jdump(res["profile"]), "messages_json": db.jdump(msgs),
                                        "updated_at": db.now()})
    gst = res["profile"].get("gstin")
    res["profile"] = public_profile(resolve_profile(res["profile"])) | {"needs_asked": res["profile"].get("needs_asked", False)}
    res["extracted"] = {k: (mask_id(v) if k in ("gstin", "udyam_number") else v) for k, v in res["extracted"].items()}
    res["has_gstin_number"] = bool(gst)
    return res


@app.put("/api/advisor/sessions/{sid}/profile")
def set_profile(sid: str, body: ProfileIn):
    s = _session(sid)
    profile = {**db.jload(s["profile_json"], {}), **body.profile}
    db.update("advisor_sessions", sid, {"profile_json": db.jdump(profile), "updated_at": db.now()})
    return {"profile": public_profile(resolve_profile(profile)), "next": advisor.next_slot(profile)}


@app.get("/api/advisor/sessions/{sid}/recommendation")
def session_recommendation(sid: str):
    s = _session(sid)
    profile = db.jload(s["profile_json"], {})
    if not profile.get("segment"):
        raise HTTPException(400, "Tell the advisor about your business first.")
    rec = recommend(profile)
    best = next(o for o in rec["options"] if o["level"] == rec["recommended"])
    rec["ai_summary"] = llm.explain(profile, best, s["language"])
    return rec


@app.post("/api/recommend")
def recommend_profile(body: ProfileIn):
    return recommend(body.profile)


# ------------------------------------------------------------------ quote and checkout

class PriceIn(BaseModel):
    session_id: str | None = None
    profile: dict | None = None
    items: dict[str, int]
    level: str | None = None


def _profile_for(body: PriceIn) -> dict:
    if body.session_id:
        return db.jload(_session(body.session_id)["profile_json"], {})
    return body.profile or {}


@app.post("/api/quote/price")
def quote_price(body: PriceIn):
    p = resolve_profile(_profile_for(body))
    errors = validate_bundle(body.items, p)
    valid_items = {k: v for k, v in body.items.items() if k in catalogue() and isinstance(v, int) and 1 <= v <= 500}
    return {"pricing": price_items(valid_items), "errors": errors, "ok": not errors}


@app.post("/api/eligibility")
def eligibility(body: PriceIn):
    """Why each catalogue product can or cannot be sold to this business (null = eligible)."""
    p = resolve_profile(_profile_for(body))
    return {pid: (product_eligibility(prod, p) or [None])[0] for pid, prod in catalogue().items()}


@app.post("/api/quotes")
def save_quote(body: PriceIn):
    res = orders.create_quote(_profile_for(body), body.items, body.level, body.session_id)
    if not res["ok"]:
        raise HTTPException(422, {"errors": res["errors"]})
    return res


@app.get("/api/quotes/{qid}")
def read_quote(qid: str):
    q = orders.get_quote(qid)
    if not q:
        raise HTTPException(404, "Quote not found.")
    q["profile"] = public_profile(q["profile"])
    return q


class CheckoutIn(BaseModel):
    quote_id: str
    business_name: str = Field(min_length=2, max_length=120)
    contact_name: str = Field(min_length=2, max_length=80)
    contact_role: str | None = None
    language: str = "en"
    payment_mode: str = "on_first_bill"
    partner_code: str | None = Field(default=None, max_length=20)


@app.post("/api/checkout")
def do_checkout(body: CheckoutIn):
    try:
        return _public_order(orders.checkout(body.quote_id, body.model_dump(), body.payment_mode, body.partner_code))
    except orders.OrderError as e:
        _err(e)


# ------------------------------------------------------------------ orders + consent + KYC

def _order(key: str) -> dict:
    o = orders.get_order(key)
    if not o:
        raise HTTPException(404, "Order not found.")
    return o


def _public_order(o: dict) -> dict:
    o = dict(o)
    o["quote"] = {k: v for k, v in o["quote"].items() if k != "profile"} | {"profile": public_profile(o["quote"]["profile"])}
    return o


@app.get("/api/orders/{key}")
def read_order(key: str):
    o = _order(key)
    o["consents"] = kyc.consents(o["id"])
    return _public_order(o)


class AdvanceIn(BaseModel):
    delay_reason: str | None = Field(default=None, max_length=200)


@app.post("/api/orders/{key}/advance")
def advance_order(key: str, body: AdvanceIn):
    try:
        return _public_order(orders.advance(_order(key)["id"], "demo", body.delay_reason))
    except orders.OrderError as e:
        _err(e)


@app.get("/api/consent/notice")
def consent_notice():
    return {"version": kyc.NOTICE_VERSION, "purposes": kyc.PURPOSES, "retention_days": 30}


class ConsentIn(BaseModel):
    choices: dict[str, bool]
    language: str = "en"


@app.post("/api/orders/{key}/consent")
def give_consent(key: str, body: ConsentIn):
    try:
        return kyc.record_consent(_order(key), body.choices, body.language)
    except kyc.KycError as e:
        _err(e)


@app.post("/api/orders/{key}/consent/withdraw")
def withdraw(key: str):
    return kyc.withdraw_consent(_order(key))


@app.get("/api/kyc/specimens")
def specimens():
    return kyc.specimen_packs()


@app.get("/api/kyc/{case_id}")
def read_case(case_id: str):
    c = kyc.get_case(case_id)
    if not c:
        raise HTTPException(404, "KYC case not found.")
    return c


@app.post("/api/kyc/{case_id}/documents")
async def upload_doc(case_id: str, doc_type: str = Form(...), file: UploadFile = File(...)):
    data = await file.read(MAX_UPLOAD_BYTES + 1)
    try:
        return kyc.upload(case_id, doc_type, data, file.content_type)
    except kyc.KycError as e:
        _err(e)


@app.get("/api/kyc/{case_id}/documents/{doc_id}/image")
def doc_image(case_id: str, doc_id: str):
    row = db.one("SELECT stored_path, purged_at FROM kyc_documents WHERE id=? AND case_id=?", (doc_id, case_id))
    if not row or row["purged_at"] or not row["stored_path"]:
        raise HTTPException(404, "Document not available (never uploaded or already deleted).")
    return FileResponse(row["stored_path"], media_type="image/png", headers={"Cache-Control": "no-store"})


class SpecimenIn(BaseModel):
    applicant: str


@app.post("/api/kyc/{case_id}/specimen")
def use_specimen(case_id: str, body: SpecimenIn):
    try:
        return kyc.load_specimen(case_id, body.applicant)
    except kyc.KycError as e:
        _err(e)


@app.post("/api/kyc/{case_id}/verify")
def verify_case(case_id: str):
    try:
        return kyc.run_verification(case_id)
    except kyc.KycError as e:
        _err(e)


class LookupIn(BaseModel):
    number: str = Field(max_length=40)


@app.post("/api/lookup/gstin")
def gstin_lookup(body: LookupIn):
    r = lookup_gstin(body.number)
    rec = r["record"] or {}
    return {"status": r["status"], "reasons": r["reasons"], "gstin_masked": mask_id(r["gstin"]),
            "trade_name": rec.get("trade_name"), "state": rec.get("state"), "source": r["source"]}


@app.post("/api/lookup/udyam")
def udyam_lookup(body: LookupIn):
    r = lookup_udyam(body.number)
    rec = r["record"] or {}
    return {"status": r["status"], "reasons": r["reasons"], "udyam_masked": mask_id(r["udyam_number"]),
            "enterprise_name": rec.get("enterprise_name"), "enterprise_type": rec.get("enterprise_type"), "source": r["source"]}


# ------------------------------------------------------------------ human assistance

class HandoffIn(BaseModel):
    reason: str = Field(min_length=2, max_length=300)
    channel: str = "callback"
    language: str = "en"
    session_id: str | None = None
    order_id: str | None = None
    step: str | None = None


@app.post("/api/handoff")
def handoff(body: HandoffIn):
    ctx = {"step": body.step}
    if body.session_id:
        s = db.one("SELECT profile_json FROM advisor_sessions WHERE id=?", (body.session_id,))
        if s:
            ctx["profile"] = public_profile(resolve_profile(db.jload(s["profile_json"], {}))) if db.jload(s["profile_json"], {}) else {}
    hid = db.new_id("H")
    db.insert("handoff_requests", {"id": hid, "session_id": body.session_id, "order_id": body.order_id,
                                   "reason": body.reason, "channel": body.channel, "language": body.language,
                                   "context_json": db.jdump(ctx), "status": "open", "created_at": db.now(),
                                   "updated_at": db.now()})
    return {"id": hid, "status": "open", "message": "A specialist will call you back within 2 working hours."}


# ------------------------------------------------------------------ back-office console

@app.get("/api/console/overview", dependencies=[Depends(console_auth)])
def console_overview():
    return analytics.overview()


@app.get("/api/console/leads", dependencies=[Depends(console_auth)])
def console_leads():
    return {"model": {k: v for k, v in analytics.score_model().items() if k != "prior"},
            "queue": analytics.priority_queue()}


@app.get("/api/console/live", dependencies=[Depends(console_auth)])
def console_live():
    """Activity generated by this prototype (not historical data)."""
    q = lambda sql: db.one(sql)["n"]  # noqa: E731
    return {
        "advisor_sessions": q("SELECT COUNT(*) n FROM advisor_sessions"),
        "quotes": q("SELECT COUNT(*) n FROM quotes"),
        "orders": q("SELECT COUNT(*) n FROM orders"),
        "activated": q("SELECT COUNT(*) n FROM orders WHERE stage='activated'"),
        "kyc_open_exceptions": q("SELECT COUNT(*) n FROM kyc_cases WHERE status IN ('manual_review','action_required')"),
        "handoffs_open": q("SELECT COUNT(*) n FROM handoff_requests WHERE status='open'"),
    }


@app.get("/api/console/kyc", dependencies=[Depends(console_auth)])
def console_kyc():
    return kyc.exception_queue()


class DecisionIn(BaseModel):
    decision: str
    reviewer: str = Field(min_length=2, max_length=60)
    reason: str = Field(min_length=3, max_length=500)


@app.post("/api/console/kyc/{case_id}/decision", dependencies=[Depends(console_auth)])
def console_decide(case_id: str, body: DecisionIn):
    try:
        return kyc.decide(case_id, body.decision, body.reviewer, body.reason)
    except kyc.KycError as e:
        _err(e)


@app.get("/api/console/orders", dependencies=[Depends(console_auth)])
def console_orders():
    return orders.list_orders()


@app.get("/api/console/handoffs", dependencies=[Depends(console_auth)])
def console_handoffs():
    rows = db.query("SELECT * FROM handoff_requests ORDER BY created_at DESC")
    for r in rows:
        r["context"] = db.jload(r.pop("context_json"), {})
    return rows


class HandoffUpdate(BaseModel):
    status: str
    assigned_to: str | None = Field(default=None, max_length=60)


@app.patch("/api/console/handoffs/{hid}", dependencies=[Depends(console_auth)])
def console_handoff_update(hid: str, body: HandoffUpdate):
    if body.status not in ("open", "assigned", "resolved"):
        raise HTTPException(400, "Invalid status.")
    db.update("handoff_requests", hid, {"status": body.status, "assigned_to": body.assigned_to, "updated_at": db.now()})
    return db.one("SELECT * FROM handoff_requests WHERE id=?", (hid,))


# Serve the built frontend when present (single-port demo); unknown paths fall back to the SPA.
_dist = ROOT / "frontend" / "dist"
if _dist.exists():
    app.mount("/assets", StaticFiles(directory=_dist / "assets"), name="assets")

    @app.get("/{path:path}", include_in_schema=False)
    def spa(path: str):
        f = (_dist / path).resolve()
        if path.startswith("api/"):
            raise HTTPException(404)
        if f.is_file() and _dist in f.parents:
            return FileResponse(f)
        return FileResponse(_dist / "index.html")
