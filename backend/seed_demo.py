"""Reset the demo and pre-load console content for a recording.

Usage (server running on :8000):  python3 backend/seed_demo.py
Creates: a KYC exception (K01 Vindhya Tours, action required), a manual review (K10 Kaveri Stays),
and one open call-back. KYC outcomes come from the real pipeline, not from this script.
"""
import sys

import httpx

c = httpx.Client(base_url=sys.argv[1] if len(sys.argv) > 1 else "http://127.0.0.1:8000", timeout=120)


def order(profile: dict, business: str, signatory: str, pack: str) -> str:
    r = c.post("/api/recommend", json={"profile": profile}).json()
    best = next(o for o in r["options"] if o["level"] == r["recommended"])
    items = {i["product_id"]: i["quantity"] for i in best["items"]}
    q = c.post("/api/quotes", json={"profile": profile, "items": items}).raise_for_status().json()
    o = c.post("/api/checkout", json={"quote_id": q["quote_id"], "business_name": business,
                                      "contact_name": signatory}).raise_for_status().json()
    case = c.post(f"/api/orders/{o['id']}/consent",
                  json={"choices": {"kyc_verification": True, "service_delivery": True}}).json()["case_id"]
    c.post(f"/api/kyc/{case}/specimen", json={"applicant": pack}).raise_for_status()
    res = c.post(f"/api/kyc/{case}/verify").raise_for_status().json()
    print(f"{o['order_no']}  {business:<28} {pack}  -> {res['status']}")
    return o["order_no"]


c.post("/api/demo/reset").raise_for_status()
order({"segment": "prof", "business_type": "Travel agency", "employees": 13, "sites": 1, "city": "Visakhapatnam",
       "needs": ["telephony", "tollfree"], "gstin": "37IHKXV5167L1ZS", "has_gstin": True},
      "Vindhya Tours & Travels", "Neha Kaur", "K01")
order({"segment": "multi", "business_type": "Budget hotel group", "employees": 40, "sites": 4, "city": "Mumbai",
       "needs": ["wifi", "cctv"], "gstin": "27QHJXK0658U1ZL", "has_gstin": True},
      "Kaveri Stays LLP", "Fatima Menon", "K10")
c.post("/api/handoff", json={"reason": "Mujhe samajh nahi aa raha kaunsa internet plan lena chahiye",
                             "language": "hi", "step": "/plans"}).raise_for_status()
print("callback request created; console ready")
