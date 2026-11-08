"""Smart KYC: document recognition, field extraction and cross-document verification.

Every check reports *where* its evidence came from:
  extracted      - read from the uploaded image by local OCR
  mock_registry  - compared with the supplied mock GSTIN / Udyam CSV
  demo_rule      - a rule evaluated locally (dates, fuzzy name match)
No genuine external verification (GSTN, Udyam portal, DigiLocker, e-sign) is performed.
"""
from __future__ import annotations

import os
import re
from datetime import date

from rapidfuzz import fuzz

from ..config import ADDRESS_PROOF_MAX_AGE_DAYS, REFERENCE_DATE
from .ocr import run_ocr
from .validators import (checksum_repair, lookup_gstin, lookup_udyam, mask_id, nearest_gstin, normalise_gstin,
                         validate_gstin_format)

DEMO_MODE = os.getenv("SYNC_DEMO_MODE", "1") == "1"
REQUIRED_DOCS = ["gst_certificate", "udyam_certificate", "address_proof", "signatory_id"]
DOC_LABELS = {"gst_certificate": "GST registration certificate", "udyam_certificate": "Udyam registration certificate",
              "address_proof": "Address proof (utility bill)", "signatory_id": "Authorised signatory ID"}
LOW_CONFIDENCE = 70.0

FIELD_LABELS = {
    "gst_certificate": [("gstin", "gstin"), ("legal_name", "legal name"), ("trade_name", "trade name"),
                        ("constitution", "constitution"), ("address", "address of principal"),
                        ("address", "place of business"), ("liability_date", "date of liability"),
                        ("registration_type", "type of registration")],
    "udyam_certificate": [("udyam_number", "udyam reg. number"), ("udyam_number", "udyam reg number"),
                          ("enterprise_name", "enterprise name"), ("major_activity", "major activity"),
                          ("city", "city"), ("state", "state"), ("registration_date", "date of registration")],
    "signatory_id": [("name", "name"), ("designation", "designation"), ("business", "for business"),
                     ("id_number", "id no."), ("valid_till", "valid till")],
    "address_proof": [("consumer_no", "consumer no."), ("billed_to", "billed to"), ("address", "supply address"),
                      ("bill_date", "bill date"), ("units", "units consumed"), ("amount_due", "amount due (inr)")],
}
MULTILINE = {"address"}
TYPE_KEYWORDS = [("gst_certificate", "gst registration"), ("udyam_certificate", "udyam registration"),
                 ("signatory_id", "signatory"), ("address_proof", "electricity bill"), ("address_proof", "supply address")]


# ------------------------------------------------------------------ extraction

def detect_type(lines: list[dict]) -> str | None:
    text = " ".join(ln["text"] for ln in lines[:6]).lower()
    for t, kw in TYPE_KEYWORDS:
        if kw in text:
            return t
    return None


def _strip_label(text: str, label: str) -> str | None:
    t = text.strip()
    if t.lower().startswith(label):
        return t[len(label):].strip(" :;|-") if not t[len(label):len(label) + 1].isalnum() else None
    return None


def extract_fields(doc_type: str, lines: list[dict]) -> dict:
    """Label/value parsing robust to values on the same or the following line, and wrapped addresses."""
    labels = FIELD_LABELS[doc_type]
    fields: dict[str, dict] = {}
    pending, last = None, None
    for ln in lines:
        text, conf = ln["text"].strip(), ln["conf"]
        if not text or text.lower().startswith(("specimen", "format for", "fictional utility", "accel ytl", "synthetic")):
            continue
        matched = False
        for key, label in sorted(labels, key=lambda kv: -len(kv[1])):
            value = _strip_label(text, label)
            if value is None:
                continue
            matched = True
            if key in fields and key in MULTILINE:          # "place of business" continues the address
                if value:
                    fields[key]["value"] += value
                    fields[key]["conf"] = min(fields[key]["conf"], conf)
                last = key
            elif value:
                fields[key] = {"value": value, "conf": conf}
                pending, last = None, key
            else:
                pending = key
            break
        if matched:
            continue
        if pending:
            fields[pending] = {"value": text, "conf": conf}
            last, pending = pending, None
        elif last in MULTILINE and last in fields:          # wrapped address line
            fields[last]["value"] += text
            fields[last]["conf"] = min(fields[last]["conf"], conf)
    for f in fields.values():
        f["value"] = re.sub(r"\s+", " ", re.sub(r"\s*-\s*(\d{6})", r" - \1", f["value"])).strip()
    return fields


def analyse_document(data: bytes, declared_type: str | None = None) -> dict:
    ocr = run_ocr(data)
    detected = detect_type(ocr["lines"])
    doc_type = detected or declared_type
    fields = extract_fields(doc_type, ocr["lines"]) if doc_type in FIELD_LABELS else {}
    header = " ".join(ln["text"] for ln in ocr["lines"][:3]).lower()
    specimen = "specimen" in header or ocr["quality"]["watermark_ratio"] > 0.001
    return {"declared_type": declared_type, "detected_type": detected, "fields": fields,
            "ocr_confidence": ocr["mean_confidence"], "quality": ocr["quality"], "specimen": specimen,
            "sha256": ocr["sha256"]}


# ------------------------------------------------------------------ verification

def _norm(s: str) -> str:
    return re.sub(r"[^a-z0-9 ]", " ", (s or "").lower()).strip()


def _compact(s: str) -> str:
    return re.sub(r"[^a-z0-9]", "", (s or "").lower())


def name_score(a: str, b: str) -> int:
    return int(fuzz.token_sort_ratio(_norm(a), _norm(b)))


def address_score(a: str, b: str) -> int:
    # Wrapped OCR lines can split words, so compare with all spaces removed.
    return int(fuzz.ratio(_compact(a), _compact(b)))


def _parse_date(s: str | None) -> date | None:
    m = re.search(r"(\d{4})[-./](\d{2})[-./](\d{2})", s or "")
    try:
        return date(int(m.group(1)), int(m.group(2)), int(m.group(3))) if m else None
    except ValueError:
        return None


def _proprietor(legal_name: str) -> str | None:
    m = re.match(r"^(.*?)\s*\(\s*prop\.?", legal_name or "", re.I)
    return m.group(1).strip() if m else None


def _trade_in_legal(legal_name: str) -> str | None:
    m = re.search(r"\(\s*prop\.?\s*(.*?)\)", legal_name or "", re.I)
    return m.group(1).strip() if m else None


class Checks:
    def __init__(self):
        self.items: list[dict] = []

    def add(self, code, label, status, detail, source, doc=None):
        self.items.append({"code": code, "label": label, "status": status, "detail": detail,
                           "source": source, "document": doc})


def verify(docs: dict[str, dict], declared: dict) -> dict:
    """docs: doc_type -> analyse_document() result. declared: what the owner told us at checkout
    (business_name, signatory_name, gstin, udyam_number)."""
    c = Checks()
    v = lambda t, k: (docs.get(t, {}).get("fields", {}).get(k) or {}).get("value", "")  # noqa: E731

    # 1. completeness + document recognition + image quality
    for t in REQUIRED_DOCS:
        d = docs.get(t)
        if not d:
            c.add("doc_missing", f"{DOC_LABELS[t]} provided", "fail", f"{DOC_LABELS[t]} was not uploaded.", "demo_rule", t)
            continue
        if d["detected_type"] and d["detected_type"] != t:
            c.add("doc_type", f"{DOC_LABELS[t]} recognised", "fail",
                  f"The file uploaded as {DOC_LABELS[t]} looks like a {DOC_LABELS[d['detected_type']]}.", "extracted", t)
        if d["quality"]["blurred"] or d["ocr_confidence"] < LOW_CONFIDENCE:
            c.add("ocr_quality", f"{DOC_LABELS[t]} readable", "review",
                  f"Image is {'blurred' if d['quality']['blurred'] else 'hard to read'} (OCR confidence "
                  f"{d['ocr_confidence']:.0f}%). Extracted values cannot be trusted; please re-upload a clear photo.",
                  "extracted", t)
        elif d["quality"].get("skew_corrected_deg"):
            c.add("ocr_quality", f"{DOC_LABELS[t]} readable", "pass",
                  f"Tilted scan straightened by {d['quality']['skew_corrected_deg']:.0f}°, then read at "
                  f"{d['ocr_confidence']:.0f}% confidence.", "extracted", t)
        if d["specimen"]:
            c.add("specimen", f"{DOC_LABELS[t]} authenticity", "demo" if DEMO_MODE else "fail",
                  "Marked 'SYNTHETIC SPECIMEN - NOT A VALID DOCUMENT'. Accepted for demo validation only; "
                  "a production system would reject it.", "extracted", t)
    unreadable = {t for t, d in docs.items() if d["quality"]["blurred"] or d["ocr_confidence"] < LOW_CONFIDENCE}

    # 2. GSTIN
    gst_raw = v("gst_certificate", "gstin")
    gst_record = None
    if "gst_certificate" in docs and "gst_certificate" not in unreadable:
        if not gst_raw:
            c.add("gstin_present", "GSTIN on certificate", "fail", "No GSTIN could be found on the certificate.",
                  "extracted", "gst_certificate")
        else:
            g = normalise_gstin(gst_raw)
            fmt = validate_gstin_format(g)
            repair = checksum_repair(g) if not fmt["valid"] else None
            if repair:
                c.add("gstin_ocr_repair", "GSTIN read correctly", "pass",
                      f"OCR read '{repair['read']}' at position {repair['position']}; the checksum and mock registry "
                      f"both confirm '{repair['corrected']}'. Corrected automatically.", "demo_rule", "gst_certificate")
                g, fmt = repair["gstin"], {"valid": True, "reasons": []}
            if not fmt["valid"]:
                near = nearest_gstin(g)
                hint = (f" A registry record differs by one character ({mask_id(near)}); the number may have "
                        "been mistyped or altered." if near else "")
                c.add("gstin_format", "GSTIN format and checksum", "fail", " ".join(fmt["reasons"]) + hint,
                      "demo_rule", "gst_certificate")
            else:
                c.add("gstin_format", "GSTIN format and checksum", "pass",
                      f"{mask_id(g)} has a valid structure and checksum (synthetic 'X' PAN type accepted).",
                      "demo_rule", "gst_certificate")
                res = lookup_gstin(g)
                if res["status"] == "not_found":
                    c.add("gstin_registry", "GSTIN found in mock registry", "fail", res["reasons"][0],
                          "mock_registry", "gst_certificate")
                else:
                    gst_record = res["record"]
                    ok = res["status"] == "active"
                    c.add("gstin_registry", "GST registration active", "pass" if ok else "fail",
                          "Mock registry status: Active." if ok else res["reasons"][0], "mock_registry", "gst_certificate")
            if declared.get("gstin") and normalise_gstin(declared["gstin"]) != g:
                c.add("gstin_declared", "GSTIN matches the one you entered", "fail",
                      "The GSTIN on the certificate differs from the one entered during sign-up.", "demo_rule",
                      "gst_certificate")

    if gst_record:
        legal, trade = v("gst_certificate", "legal_name"), v("gst_certificate", "trade_name")
        s_legal = name_score(legal, gst_record["legal_name"])
        s_trade = name_score(trade, gst_record["trade_name"])
        worst = min(s_legal, s_trade)
        status = "pass" if worst >= 92 else "review" if worst >= 80 else "fail"
        detail = "Legal and trade name match the mock registry."
        if status != "pass":
            which = "Legal name" if s_legal <= s_trade else "Trade name"
            got, exp = (legal, gst_record["legal_name"]) if s_legal <= s_trade else (trade, gst_record["trade_name"])
            detail = f"{which} on certificate '{got}' does not match registry '{exp}' ({worst}% similar)."
        c.add("gst_name_registry", "Certificate names match registry", status, detail, "mock_registry", "gst_certificate")
        embedded = _trade_in_legal(legal)
        if embedded and name_score(embedded, trade) < 85:
            c.add("gst_internal", "Certificate is internally consistent", "fail",
                  f"Legal name says proprietor of '{embedded}' but trade name is '{trade}'.", "extracted", "gst_certificate")
        a = address_score(v("gst_certificate", "address"), gst_record["principal_place_of_business"])
        c.add("gst_address_registry", "Business address matches registry",
              "pass" if a >= 90 else "review" if a >= 75 else "fail",
              f"Principal place of business is {a}% similar to the registry address.", "mock_registry", "gst_certificate")

    # 3. Udyam
    if "udyam_certificate" in docs and "udyam_certificate" not in unreadable:
        u_raw = v("udyam_certificate", "udyam_number")
        if not u_raw:
            c.add("udyam_present", "Udyam number on certificate", "fail",
                  "The Udyam registration number field is blank on the certificate.", "extracted", "udyam_certificate")
        else:
            res = lookup_udyam(u_raw)
            if res["status"] == "invalid_format":
                c.add("udyam_format", "Udyam number format", "fail", res["reasons"][0], "demo_rule", "udyam_certificate")
            elif res["status"] == "not_found":
                c.add("udyam_registry", "Udyam number found in mock registry", "fail", res["reasons"][-1],
                      "mock_registry", "udyam_certificate")
            else:
                rec = res["record"]
                c.add("udyam_registry", "Udyam number found in mock registry", "pass",
                      f"{mask_id(res['udyam_number'])} found ({rec['enterprise_type']} enterprise). District code 00 "
                      "is the dataset's fictional code and is accepted.", "mock_registry", "udyam_certificate")
                s = name_score(v("udyam_certificate", "enterprise_name"), rec["enterprise_name"])
                loc_ok = _norm(v("udyam_certificate", "city")) == _norm(rec["city"]) and \
                    _norm(v("udyam_certificate", "state")) == _norm(rec["state"])
                c.add("udyam_match", "Udyam details match registry",
                      "pass" if s >= 92 and loc_ok else "review" if s >= 80 else "fail",
                      f"Enterprise name {s}% similar; city/state {'match' if loc_ok else 'differ'}.",
                      "mock_registry", "udyam_certificate")
                diffs = []
                if _parse_date(v("udyam_certificate", "registration_date")) != _parse_date(rec["date_of_registration"]):
                    diffs.append("registration date")
                if _norm(v("udyam_certificate", "major_activity")) != _norm(rec["major_activity"]):
                    diffs.append(f"major activity (registry: {rec['major_activity']})")
                if diffs:
                    c.add("udyam_minor", "Udyam secondary fields", "info",
                          "Differs from mock registry on " + " and ".join(diffs) + ". Logged for the reviewer; not used "
                          "to block onboarding.", "mock_registry", "udyam_certificate")
            if declared.get("udyam_number") and u_raw and lookup_udyam(u_raw)["udyam_number"] != lookup_udyam(declared["udyam_number"])["udyam_number"]:
                c.add("udyam_declared", "Udyam number matches sign-up", "fail",
                      "The Udyam number on the certificate differs from the one on record.", "demo_rule", "udyam_certificate")

    # 4. Business name consistency across every document and the sign-up declaration
    names = {"declared": declared.get("business_name"), "gst_certificate": v("gst_certificate", "trade_name"),
             "udyam_certificate": v("udyam_certificate", "enterprise_name"), "signatory_id": v("signatory_id", "business"),
             "address_proof": v("address_proof", "billed_to")}
    names = {k: n for k, n in names.items() if n and k not in unreadable}
    anchor = names.get("declared") or names.get("gst_certificate")
    if anchor and len(names) > 1:
        bad = [(k, n, name_score(n, anchor)) for k, n in names.items() if name_score(n, anchor) < 90]
        c.add("name_consistency", "Business name consistent across documents", "pass" if not bad else "fail",
              f"'{anchor}' appears on all {len(names)} sources." if not bad else
              "; ".join(f"{DOC_LABELS.get(k, 'Sign-up')} shows '{n}' ({s}% similar)" for k, n, s in bad), "demo_rule")

    # 5. Address proof: matches GST address and is recent
    if "address_proof" in docs and "address_proof" not in unreadable:
        ref = (gst_record or {}).get("principal_place_of_business") or v("gst_certificate", "address")
        bill_addr = v("address_proof", "address")
        if ref and bill_addr:
            a = address_score(bill_addr, ref)
            c.add("address_match", "Address proof matches GST address", "pass" if a >= 90 else "review" if a >= 75 else "fail",
                  f"Supply address is {a}% similar to the GST principal place of business.", "demo_rule", "address_proof")
        bd = _parse_date(v("address_proof", "bill_date"))
        if not bd:
            c.add("address_fresh", "Address proof is recent", "review", "Bill date could not be read.", "extracted", "address_proof")
        else:
            age = (REFERENCE_DATE - bd).days
            if age < 0:
                c.add("address_fresh", "Address proof is recent", "fail",
                      f"Bill date {bd} is after the reference date {REFERENCE_DATE}.", "demo_rule", "address_proof")
            else:
                c.add("address_fresh", "Address proof is recent", "pass" if age <= ADDRESS_PROOF_MAX_AGE_DAYS else "fail",
                      f"Bill dated {bd} is {age} days old (limit {ADDRESS_PROOF_MAX_AGE_DAYS} days, reference date "
                      f"{REFERENCE_DATE}).", "demo_rule", "address_proof")

    # 6. Signatory identity
    if "signatory_id" in docs and "signatory_id" not in unreadable:
        sig = v("signatory_id", "name")
        expected = [(declared.get("signatory_name"), "the authorised signatory named at sign-up")]
        prop = _proprietor((gst_record or {}).get("legal_name") or v("gst_certificate", "legal_name"))
        if prop:
            expected.append((prop, "the proprietor on the GST registration"))
        for exp, who in expected:
            if not exp:
                continue
            s = name_score(sig, exp)
            c.add("signatory_match", f"Signatory ID matches {who}", "pass" if s >= 90 else "review",
                  f"'{sig}' matches." if s >= 90 else f"ID belongs to '{sig}' but we expected '{exp}' ({s}% similar). "
                  "A different person may be authorised; a reviewer must see an authorisation letter.",
                  "demo_rule", "signatory_id")
        vt = _parse_date(v("signatory_id", "valid_till"))
        c.add("signatory_valid", "Signatory ID within validity", "pass" if vt and vt >= REFERENCE_DATE else "fail",
              f"Valid till {vt}." if vt else "Validity date not readable.", "extracted", "signatory_id")

    return summarise(c.items)


def summarise(items: list[dict]) -> dict:
    fails = [i for i in items if i["status"] == "fail"]
    reviews = [i for i in items if i["status"] == "review"]
    if fails:
        status, msg = "action_required", "Some details could not be verified. Fix the items below or ask for help."
    elif reviews:
        status, msg = "manual_review", "A KYC specialist will review a few items, usually within 4 working hours."
    else:
        status, msg = "passed_demo", "All demo checks passed against the mock registries."
    return {"status": status, "message": msg, "checks": items,
            "counts": {s: sum(1 for i in items if i["status"] == s) for s in ("pass", "fail", "review", "info", "demo")},
            "disclaimer": "Demo verification against supplied mock registries only. Genuine external verification "
                          "(GSTN, Udyam portal, DigiLocker, e-sign) was not performed."}
