"""Reproducible demo journeys built from real records in smb_leads.csv.

Each scenario names a dataset lead, the specimen KYC pack for the same business, and a short
scripted conversation for the advisor. Expected KYC outcomes are NOT stored here: the KYC engine
works them out from the images.
"""
from __future__ import annotations

from .data import SEGMENT_CODES, lead

SCENARIOS = [
    {"id": "micro-salon", "lead_id": "L00115", "kyc_pack": "K06", "title": "Neighbourhood salon",
     "focus": "Affordable connectivity, WhatsApp bookings and UPI billing",
     "script": ["I run a unisex salon in Jaipur with 1 staff", "Home broadband",
                "I need WhatsApp for bookings and a billing machine with UPI", "Yes, 08YKZXS5189L1ZO", "Rs 3000"]},
    {"id": "prof-clinic", "lead_id": "L01287", "kyc_pack": "K02", "title": "Dental clinic",
     "focus": "Stable internet, clinic email, device security and a phone system",
     "script": ["We are a dental clinic in Kolkata, 5 staff, 1 site", "Business broadband",
                "Clinic email, antivirus for our PCs and a phone system with call recording",
                "Yes 19EOGXH4115Y1ZL", "Rs 9000"]},
    {"id": "multi-retail", "lead_id": "L03558", "kyc_pack": "K12", "title": "11-store electronics chain",
     "focus": "One bill for 11 stores, failover, CCTV and central management",
     "script": ["Electronics retail chain with 11 stores in Visakhapatnam, 44 employees",
                "Different provider at each branch",
                "CCTV in every store, backup internet, central management and GPS for delivery vans",
                "Yes 37NBLXS1145E1ZU", "Not sure"]},
    {"id": "mfg-workshop", "lead_id": "L03571", "kyc_pack": "K03", "title": "Furniture workshop",
     "focus": "Dedicated bandwidth, machine monitoring IoT, CCTV and security",
     "script": ["Furniture workshop in Nagpur, 15 workers, 1 site", "Leased line",
                "Monitor our machines, CCTV and antivirus", "Yes 27XUIXG0767D1ZP", "Rs 30000"]},
    {"id": "kyc-exception", "lead_id": "L00045", "kyc_pack": "K01", "title": "Travel agency (KYC exception)",
     "focus": "What happens when registry status and documents do not line up",
     "script": ["Travel agency in Visakhapatnam, 13 staff, 1 office", "Home broadband",
                "A business phone system and a toll free number", "yes 37IHKXV5167L1ZS", "Rs 10000"]},
]


def _profile(row: dict) -> dict:
    return {
        "business_type": row["business_type"], "segment": SEGMENT_CODES[row["segment"]], "city": row["city"],
        "city_tier": int(row["city_tier"]), "state": row["state"], "employees": int(row["employee_count"]),
        "sites": int(row["num_sites"]), "current_internet": row["current_internet"],
        "current_provider": row["current_provider"], "monthly_spend": int(row["monthly_telecom_spend_inr"]),
        "has_gstin": row["has_gstin"] == "Y", "gstin": row["gstin"], "has_udyam": row["has_udyam"] == "Y",
        "udyam_number": row["udyam_number"],
    }


def get(sid: str) -> dict | None:
    s = next((x for x in SCENARIOS if x["id"] == sid), None)
    if not s:
        return None
    row = lead(s["lead_id"])
    return {**s, "business_name": row["business_name"], "contact_name": row["contact_name"],
            "contact_role": row["contact_role"], "segment": row["segment"], "city": row["city"],
            "dataset_profile": _profile(row)}


def all_public() -> list[dict]:
    out = []
    for s in SCENARIOS:
        g = get(s["id"])
        out.append({k: g[k] for k in ("id", "title", "focus", "business_name", "contact_name", "contact_role",
                                      "segment", "city", "lead_id", "kyc_pack", "script")})
    return out
