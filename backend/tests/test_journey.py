"""API-level tests: advisor -> recommendation -> quote -> checkout -> consent -> KYC -> order -> console."""
from datetime import date

from app.orders import expected_dates
from app.scenarios import SCENARIOS


def run_advisor(client, script):
    sid = client.post("/api/advisor/sessions", json={"language": "en"}).json()["session_id"]
    expecting = "business_type"
    for msg in script:
        res = client.post(f"/api/advisor/sessions/{sid}/messages", json={"text": msg, "expecting": expecting}).json()
        expecting = res["next"]
    return sid, res


def journey(client, scenario_id, pay="on_first_bill"):
    s = next(x for x in SCENARIOS if x["id"] == scenario_id)
    sid, res = run_advisor(client, s["script"])
    assert res["done"], res
    rec = client.get(f"/api/advisor/sessions/{sid}/recommendation").json()
    opt = next(o for o in rec["options"] if o["level"] == rec["recommended"])
    items = {i["product_id"]: i["quantity"] for i in opt["items"]}
    q = client.post("/api/quotes", json={"session_id": sid, "items": items, "level": opt["level"]}).json()
    from app.data import lead
    row = lead(s["lead_id"])
    order = client.post("/api/checkout", json={"quote_id": q["quote_id"], "business_name": row["business_name"],
                                               "contact_name": row["contact_name"], "payment_mode": pay}).json()
    return s, sid, q, order


def test_health_and_data_loading(client):
    h = client.get("/api/health").json()
    assert h["status"] == "ok" and h["products"] == 25 and h["leads"] == 5000 and h["ocr"]
    assert h["llm"] is False


def test_advisor_understands_multiple_facts_in_one_message(client):
    sid, res = run_advisor(client, ["I run a dental clinic in Kochi with 12 staff"])
    p = res["profile"]
    assert (p["segment"], p["city"], p["employees"], p["city_tier"]) == ("prof", "Kochi", 12, 2)
    assert res["next"] == "sites"


def test_advisor_hindi_and_tamil(client):
    _, res = run_advisor(client, ["मेरी किराना दुकान है लुधियाना में", "3 लोग", "हॉटस्पॉट", "व्हाट्सएप और बिलिंग चाहिए", "नहीं", "3000"])
    assert res["done"] and res["profile"]["segment"] == "micro" and set(res["profile"]["needs"]) == {"pos", "whatsapp"}
    _, res = run_advisor(client, ["கோயம்புத்தூரில் எனக்கு தொழிற்சாலை உள்ளது", "90 ஊழியர்", "1", "லீஸ்டு லைன்",
                                  "இயந்திர கண்காணிப்பு", "ஆம்", "தெரியாது"])
    assert res["done"] and res["profile"]["segment"] == "mfg" and res["profile"]["city"] == "Coimbatore"


def test_gstin_never_returned_in_clear(client):
    sid, res = run_advisor(client, ["Kirana store in Delhi, 2 staff", "hotspot", "billing", "yes 27XUIXG0767D1ZP"])
    assert "27XUIXG0767D1ZP" not in str(res)


def test_quote_api_rejects_invalid_bundle(client):
    r = client.post("/api/quotes", json={"profile": {"segment": "prof", "employees": 5, "city": "Mumbai"},
                                         "items": {"P09": 1, "P07": 1}})
    assert r.status_code == 422
    live = client.post("/api/quote/price", json={"profile": {"segment": "prof", "employees": 5, "city": "Mumbai"},
                                                 "items": {"P09": 1, "P07": 1}}).json()
    assert not live["ok"] and live["pricing"]["monthly_min"] == 499 + 299


def test_full_happy_journey_reaches_activation(client):
    s, _, q, order = journey(client, "mfg-workshop", pay="pay_now")
    assert order["stage"] == "kyc" and order["payment_status"] == "confirmed"
    created = date.fromisoformat(order["created_at"][:10])
    assert order["expected_activation"] == expected_dates(created, q["pricing"]["install_days"])["activated"]
    assert order["timeline"][-1]["expected"] == order["expected_activation"]
    # KYC cannot be skipped
    assert client.post(f"/api/orders/{order['id']}/advance", json={}).status_code == 400
    # consent is mandatory before documents
    assert client.post(f"/api/orders/{order['id']}/consent", json={"choices": {"kyc_verification": True}}).status_code == 400
    c = client.post(f"/api/orders/{order['id']}/consent",
                    json={"choices": {"kyc_verification": True, "service_delivery": True}}).json()
    case = c["case_id"]
    assert len(client.post(f"/api/kyc/{case}/specimen", json={"applicant": s["kyc_pack"]}).json()) == 4
    res = client.post(f"/api/kyc/{case}/verify").json()
    assert res["status"] == "passed_demo"
    o = client.get(f"/api/orders/{order['order_no']}").json()
    assert o["stage"] == "serviceability"
    # once KYC has passed, documents are locked so the order cannot regress
    assert client.post(f"/api/kyc/{case}/specimen", json={"applicant": "K01"}).status_code == 400
    for _ in range(3):
        o = client.post(f"/api/orders/{order['id']}/advance", json={}).json()
    assert o["stage"] == "activated"
    assert all(t["state"] == "done" for t in o["timeline"])


def test_kyc_exception_goes_to_console_and_reviewer_can_approve(client, console):
    _, _, _, order = journey(client, "kyc-exception")
    case = client.post(f"/api/orders/{order['id']}/consent",
                       json={"choices": {"kyc_verification": True, "service_delivery": True}}).json()["case_id"]
    client.post(f"/api/kyc/{case}/specimen", json={"applicant": "K01"})
    res = client.post(f"/api/kyc/{case}/verify").json()
    assert res["status"] == "action_required"
    o = client.get(f"/api/orders/{order['id']}").json()
    assert o["stage"] == "kyc" and o["delay_reason"] and o["pending_actions"]
    assert client.get("/api/console/kyc").status_code == 401
    queue = client.get("/api/console/kyc", headers=console).json()
    assert any(r["id"] == case and r["issues"] for r in queue)
    assert client.post(f"/api/console/kyc/{case}/decision", headers=console,
                       json={"decision": "approved", "reviewer": "QA", "reason": ""}).status_code == 422
    client.post(f"/api/console/kyc/{case}/decision", headers=console,
                json={"decision": "approved", "reviewer": "KYC desk", "reason": "GST re-registration verified offline"})
    assert client.get(f"/api/orders/{order['id']}").json()["stage"] == "serviceability"


def test_upload_validation_and_consent_withdrawal(client):
    _, _, _, order = journey(client, "prof-clinic")
    case = client.post(f"/api/orders/{order['id']}/consent",
                       json={"choices": {"kyc_verification": True, "service_delivery": True}}).json()["case_id"]
    bad = client.post(f"/api/kyc/{case}/documents", data={"doc_type": "gst_certificate"},
                      files={"file": ("x.png", b"not an image", "image/png")})
    assert bad.status_code == 400
    from .conftest import SPECIMENS
    ok = client.post(f"/api/kyc/{case}/documents", data={"doc_type": "gst_certificate"},
                     files={"file": ("a.png", (SPECIMENS / "K02_gst_certificate.png").read_bytes(), "image/png")}).json()
    assert ok["fields"]["gstin"]["value"].startswith("19") and "•" in ok["fields"]["gstin"]["value"]
    w = client.post(f"/api/orders/{order['id']}/consent/withdraw").json()
    assert w["documents_deleted"] == 1
    assert client.post(f"/api/kyc/{case}/verify").status_code == 400


def test_delay_and_handoff(client, console):
    _, sid, _, order = journey(client, "micro-salon")
    o = client.post(f"/api/orders/{order['id']}/advance", json={"delay_reason": "Engineer slot moved"}).json()
    assert o["delay_reason"] == "Engineer slot moved" and o["expected_activation"] > order["expected_activation"]
    h = client.post("/api/handoff", json={"reason": "Need help with documents", "session_id": sid, "step": "kyc"}).json()
    assert h["status"] == "open"
    assert any(x["id"] == h["id"] for x in client.get("/api/console/handoffs", headers=console).json())


def test_console_analytics_match_case_baseline(client, console):
    o = client.get("/api/console/overview", headers=console).json()
    assert [f["count"] for f in o["funnel"]] == [5000, 3406, 1974, 861, 588, 368]
    assert o["totals"]["blended_cac"] == 15053 and o["mean_cac_activated_only"] < 6000
    assert o["totals"]["days_to_activate"] == 17.6
    gst = {d["key"]: d["conversion_pct"] for d in o["dimensions"]["has_gstin"]}
    assert (gst["Y"], gst["N"]) == (9.6, 2.0)
    leads = client.get("/api/console/leads", headers=console).json()
    assert leads["queue"] and 0.5 < leads["model"]["backtest"]["auc"] < 1
    assert "preferred_language" not in str(leads["model"]["weights"])
