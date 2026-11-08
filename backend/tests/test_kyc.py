"""KYC tests run the real OCR pipeline on the supplied specimen images."""
from datetime import timedelta

import pytest

from app.config import REFERENCE_DATE
from app.kyc.pipeline import REQUIRED_DOCS, analyse_document, summarise, verify
from app.kyc.validators import (checksum_repair, gstin_checksum, lookup_gstin, lookup_udyam, mask_id,
                                validate_gstin_format)

from .conftest import SPECIMENS


def pack(k):
    return {t: analyse_document((SPECIMENS / f"{k}_{t}.png").read_bytes(), t)
            for t in REQUIRED_DOCS if (SPECIMENS / f"{k}_{t}.png").exists()}


def statuses(result, code):
    return [c["status"] for c in result["checks"] if c["code"] == code]


@pytest.fixture(scope="module")
def packs():
    return {k: pack(k) for k in ["K01", "K02", "K03", "K04", "K05", "K06", "K07", "K10", "K11"]}


# ---- identifiers

def test_valid_synthetic_gstin_with_x_pan_type():
    assert validate_gstin_format("27XUIXG0767D1ZP")["valid"]
    assert lookup_gstin("27XUIXG0767D1ZP")["status"] == "active"


def test_gstin_checksum_and_unknown_gstin():
    first14 = "27XUIXG0767D1Z"
    assert gstin_checksum(first14) == "P"
    bad = first14 + ("Q" if gstin_checksum(first14) != "Q" else "R")
    assert lookup_gstin(bad)["status"] == "invalid_format"
    unknown = "27AAAXA0000A1Z" + gstin_checksum("27AAAXA0000A1Z")
    assert lookup_gstin(unknown)["status"] == "not_found"


def test_cancelled_and_suspended_gstin():
    assert lookup_gstin("37IHKXV5167L1ZS")["status"] == "cancelled"
    from app.data import gstin_registry
    s = next(g for g, r in gstin_registry().items() if r["status"] == "Suspended")
    assert lookup_gstin(s)["status"] == "suspended"


def test_udyam_lookup_match_unknown_and_format():
    assert lookup_udyam("UDYAM-MH-00- 9516696")["status"] == "found"
    assert lookup_udyam("UDYAM-MH-00-0000001")["status"] == "not_found"
    assert lookup_udyam("UDYAM-123")["status"] == "invalid_format"


def test_checksum_repair_fixes_ocr_glyph_swaps_but_not_real_alterations():
    assert checksum_repair("37THKXV5167L1ZS")["gstin"] == "37IHKXV5167L1ZS"  # I read as T
    assert checksum_repair("08YKZXS8189L1ZO") is None                     # 5 changed to 8 on the document


def test_masking():
    assert mask_id("27XUIXG0767D1ZP") == "27•••••••••D1ZP"
    assert "9516696" not in mask_id("UDYAM-MH-00-9516696")


# ---- documents

def test_document_type_recognition_and_field_extraction(packs):
    gst = packs["K03"]["gst_certificate"]
    assert gst["detected_type"] == "gst_certificate"
    assert gst["fields"]["gstin"]["value"] == "27XUIXG0767D1ZP"
    assert gst["fields"]["address"]["value"].endswith("Nagpur, Maharashtra - 411231")
    assert packs["K03"]["signatory_id"]["fields"]["name"]["value"] == "Joseph Singh"
    assert all(0 < f["conf"] <= 100 for f in gst["fields"].values())
    assert gst["fields"]["legal_name"]["conf"] > 90


def test_specimen_watermark_detected_on_every_document(packs):
    assert all(d["specimen"] for p in packs.values() for d in p.values())


def test_clean_pack_passes_demo_validation_only(packs):
    r = verify(packs["K03"], {"business_name": "Ganesh Woodcraft", "signatory_name": "Joseph Singh",
                              "gstin": "27XUIXG0767D1ZP", "udyam_number": "UDYAM-MH-00-9516696"})
    assert r["status"] == "passed_demo"
    assert "not performed" in r["disclaimer"]
    assert statuses(r, "specimen") == ["demo"] * 4


def test_tilted_scan_is_straightened(packs):
    d = packs["K02"]["gst_certificate"]
    assert abs(d["quality"]["skew_corrected_deg"]) >= 3
    assert d["fields"]["gstin"]["value"] == "19EOGXH4115Y1ZL"


def test_low_ocr_confidence_routes_to_manual_review(packs):
    r = verify(packs["K04"], {"business_name": "Saffron Dental Care LLP", "signatory_name": "Fatima Pillai"})
    assert "review" in statuses(r, "ocr_quality")
    assert r["status"] == "manual_review"


def test_missing_document(packs):
    r = verify(packs["K05"], {"business_name": "Balaji Realty LLP", "signatory_name": "Anita Shah"})
    assert statuses(r, "doc_missing") == ["fail"]
    assert r["status"] == "action_required"


def test_cancelled_gstin_and_blank_udyam_number(packs):
    r = verify(packs["K01"], {"business_name": "Vindhya Tours & Travels", "signatory_name": "Neha Kaur"})
    assert statuses(r, "gstin_registry") == ["fail"]
    assert statuses(r, "udyam_present") == ["fail"]


def test_altered_gstin_fails_checksum(packs):
    r = verify(packs["K06"], {"business_name": "Saffron Unisex Salon", "signatory_name": "Pooja Shah",
                              "gstin": "08YKZXS5189L1ZO"})
    assert statuses(r, "gstin_format") == ["fail"]
    assert statuses(r, "gstin_declared") == ["fail"]


def test_name_mismatch_inside_certificate(packs):
    r = verify(packs["K07"], {"business_name": "Neelgiri Physio Clinic", "signatory_name": "Neha Banerjee"})
    assert statuses(r, "gst_internal") == ["fail"]


def test_signatory_mismatch_goes_to_review(packs):
    r = verify(packs["K10"], {"business_name": "Kaveri Stays LLP", "signatory_name": "Fatima Menon"})
    assert "review" in statuses(r, "signatory_match")


def test_expired_address_proof(packs):
    r = verify(packs["K11"], {"business_name": "Trinity Bake House Pvt Ltd", "signatory_name": "Vikram Pillai"})
    assert statuses(r, "address_fresh") == ["fail"]
    assert "257 days" in next(c["detail"] for c in r["checks"] if c["code"] == "address_fresh")


def test_address_mismatch_and_business_name_mismatch(packs):
    import copy
    docs = copy.deepcopy(packs["K03"])
    docs["address_proof"]["fields"]["address"]["value"] = "Plot 9, MIDC, Pune, Maharashtra - 411001"
    docs["address_proof"]["fields"]["billed_to"]["value"] = "Someone Else Traders"
    r = verify(docs, {"business_name": "Ganesh Woodcraft", "signatory_name": "Joseph Singh"})
    assert statuses(r, "address_match") == ["fail"]
    assert statuses(r, "name_consistency") == ["fail"]


def test_bill_dated_exactly_90_days_ago_passes_91_fails(packs):
    import copy
    for days, expected in [(90, "pass"), (91, "fail")]:
        docs = copy.deepcopy(packs["K03"])
        docs["address_proof"]["fields"]["bill_date"]["value"] = (REFERENCE_DATE - timedelta(days=days)).isoformat()
        r = verify(docs, {"business_name": "Ganesh Woodcraft", "signatory_name": "Joseph Singh"})
        assert statuses(r, "address_fresh") == [expected]


def test_summary_routing():
    assert summarise([{"status": "pass"}, {"status": "review"}])["status"] == "manual_review"
    assert summarise([{"status": "review"}, {"status": "fail"}])["status"] == "action_required"
    assert summarise([{"status": "pass"}, {"status": "demo"}])["status"] == "passed_demo"
