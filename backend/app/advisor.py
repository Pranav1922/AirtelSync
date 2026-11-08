"""Guided conversational advisor.

A short slot-filling dialogue. Every message is scanned for *all* slots, so "I run a dental
clinic in Kochi with 12 staff" answers three questions at once. Understanding is rule-based
(English, Hindi, Tamil keywords) and runs offline; an LLM, if configured, only helps parse
messages the rules could not understand. Product choice is always done by recommend.py.
"""
from __future__ import annotations

import re

from . import llm
from .data import business_types, city_tiers
from .kyc.validators import GSTIN_RE, UDYAM_RE, lookup_gstin, normalise_gstin, normalise_udyam

SLOTS = ["business_type", "city", "employees", "sites", "current_internet", "needs", "gstin", "budget"]

SEGMENT_KEYWORDS = {
    "mfg": ["factory", "manufacturing", "manufacturer", "manufacture", "workshop", "plant", "unit", "printing press", "moulding", "fabrication",
            "फैक्ट्री", "कारखाना", "उत्पादन", "தொழிற்சாலை", "உற்பத்தி", "பட்டறை"],
    "multi": ["chain", "branches", "outlets", "stores across", "franchise", "शाखाएं", "चेन", "கிளைகள்", "சங்கிலி"],
    "prof": ["clinic", "office", "ca firm", "chartered", "law", "lawyer", "advocate", "coaching", "agency", "studio",
             "lab", "consultant", "consultancy", "doctor", "dentist", "clinics", "offices", "क्लिनिक", "दफ्तर", "ऑफिस", "कोचिंग", "वकील", "டாக்டர்",
             "அலுவலகம்", "மருத்துவமனை", "கிளினிக்", "பயிற்சி மையம்"],
    "micro": ["shop", "shops", "store", "kirana", "salon", "parlour", "bakery", "pharmacy", "medical store", "boutique",
              "repair", "dukaan", "दुकान", "किराना", "सैलून", "बेकरी", "கடை", "சலூன்", "மருந்தகம்", "பேக்கரி"],
}
GENERIC_TYPE = {"micro": "Retail shop", "prof": "Professional office", "multi": "Multi-site business",
                "mfg": "Manufacturing unit"}
KEYWORD_TYPE = {"kirana": "Kirana store", "किराना": "Kirana store", "salon": "Salon", "सैलून": "Salon", "சலூன்": "Salon",
                "bakery": "Bakery", "बेकरी": "Bakery", "பேக்கரி": "Bakery", "pharmacy": "Pharmacy",
                "மருந்தகம்": "Pharmacy", "boutique": "Boutique", "clinic": "Clinic", "क्लिनिक": "Clinic",
                "கிளினிக்": "Clinic", "dentist": "Dental clinic", "coaching": "Coaching centre", "कोचिंग": "Coaching centre",
                "lawyer": "Law office", "advocate": "Law office", "वकील": "Law office", "ca firm": "CA firm",
                "chartered": "CA firm", "factory": "Manufacturing unit", "फैक्ट्री": "Manufacturing unit",
                "कारखाना": "Manufacturing unit", "தொழிற்சாலை": "Manufacturing unit", "workshop": "Furniture workshop",
                "printing press": "Printing press"}
CITY_ALIASES = {"दिल्ली": "Delhi", "मुंबई": "Mumbai", "बेंगलुरु": "Bengaluru", "बैंगलोर": "Bengaluru", "चेन्नई": "Chennai",
                "हैदराबाद": "Hyderabad", "पुणे": "Pune", "कोलकाता": "Kolkata", "जयपुर": "Jaipur", "लखनऊ": "Lucknow",
                "इंदौर": "Indore", "भोपाल": "Bhopal", "पटना": "Patna", "नागपुर": "Nagpur", "अहमदाबाद": "Ahmedabad",
                "सूरत": "Surat", "लुधियाना": "Ludhiana", "சென்னை": "Chennai", "கோயம்புத்தூர்": "Coimbatore",
                "கோவை": "Coimbatore", "பெங்களூரு": "Bengaluru", "மும்பை": "Mumbai", "டெல்லி": "Delhi",
                "ஹைதராபாத்": "Hyderabad", "கொச்சி": "Kochi", "மைசூரு": "Mysuru", "bangalore": "Bengaluru",
                "bombay": "Mumbai", "madras": "Chennai", "cochin": "Kochi", "vizag": "Visakhapatnam", "mysore": "Mysuru",
                "calcutta": "Kolkata", "baroda": "Vadodara"}
INTERNET_KEYWORDS = {
    "Mobile hotspot": ["hotspot", "mobile data", "phone internet", "हॉटस्पॉट", "मोबाइल डेटा", "ஹாட்ஸ்பாட்", "மொபைல் டேட்டா"],
    "Home broadband": ["home broadband", "home wifi", "home wi-fi", "घर का ब्रॉडबैंड", "வீட்டு பிராட்பேண்ட்"],
    "Business broadband": ["business broadband", "fibre", "fiber", "broadband", "ब्रॉडबैंड", "பிராட்பேண்ட்"],
    "Leased line": ["leased line", "ill", "dedicated line", "लीज्ड लाइन", "லீஸ்டு லைன்"],
    "Mixed per site": ["different provider", "mixed", "each branch", "अलग-अलग", "வெவ்வேறு"],
    "None": ["no internet", "nothing", "none", "इंटरनेट नहीं", "இணையம் இல்லை"],
}
NEED_KEYWORDS = {
    "pos": ["pos", "billing", "upi", "card payment", "invoice", "बिलिंग", "यूपीआई", "பில்லிங்", "யுபிஐ"],
    "whatsapp": ["whatsapp", "व्हाट्सएप", "வாட்ஸ்அப்"],
    "sms": ["sms", "एसएमएस", "குறுஞ்செய்தி"],
    "email": ["email", "e-mail", "mail", "office suite", "ईमेल", "மின்னஞ்சல்"],
    "data_backup": ["backup", "storage", "बैकअप", "காப்புப்பிரதி"],
    "website": ["website", "domain", "वेबसाइट", "இணையதளம்"],
    "cctv": ["cctv", "camera", "cameras", "surveillance", "सीसीटीवी", "कैमरा", "கேமரா", "சிசிடிவி"],
    "wifi": ["wifi", "wi-fi", "guest", "वाईफाई", "வைஃபை"],
    "endpoint": ["antivirus", "virus", "ransomware", "एंटीवायरस", "வைரஸ்"],
    "firewall": ["firewall", "cyber", "security", "hack", "सुरक्षा", "பாதுகாப்பு"],
    "failover": ["failover", "backup internet", "downtime", "uptime", "never go down", "बैकअप इंटरनेट", "காப்பு இணையம்"],
    "telephony": ["ivr", "call recording", "phone system", "landline", "telephony", "कॉल रिकॉर्डिंग", "அழைப்பு பதிவு"],
    "tollfree": ["toll free", "toll-free", "1800", "टोल फ्री", "கட்டணமில்லா"],
    "mobile": ["sim", "mobile line", "postpaid", "सिम", "சிம்"],
    "iot": ["machines", "machine monitoring", "iot", "sensor", "energy", "मशीन", "இயந்திர"],
    "fleet": ["vehicle", "vehicles", "fleet", "gps", "truck", "trucks", "delivery van", "delivery vans", "गाड़ी", "वाहन", "வாகனம்"],
    "multisite_mgmt": ["sd-wan", "central management", "manage all branches", "केंद्रीय", "மையக் கட்டுப்பாடு"],
    "static_ip": ["static ip", "fixed ip", "remote access", "स्टैटिक आईपी", "நிலையான ஐபி"],
}
YES = ["yes", "yeah", "haan", "han", "हाँ", "हां", "ஆம்", "aam", "have", "registered"]
NO = ["no", "nahi", "नहीं", "இல்லை", "illai", "don't", "dont", "not registered"]
CHIPS = {
    "business_type": ["Kirana store", "Pharmacy", "Dental clinic", "CA firm", "Restaurant chain", "Textile unit"],
    "city": ["Delhi", "Mumbai", "Chennai", "Bengaluru", "Ludhiana", "Coimbatore"],
    "employees": ["1-5", "6-20", "21-60", "60+"],
    "sites": ["1", "2-3", "4-10"],
    "current_internet": ["Mobile hotspot", "Home broadband", "Business broadband", "Leased line", "None"],
    "needs": list(NEED_KEYWORDS),
    "gstin": ["yes", "no"],
    "budget": ["Under Rs 3,000", "Rs 3,000-10,000", "Rs 10,000-30,000", "Above Rs 30,000", "Not sure"],
}
RANGE_MAP = {"1-5": 3, "6-20": 12, "21-60": 40, "60+": 80, "2-3": 3, "4-10": 6,
             "Under Rs 3,000": 3000, "Rs 3,000-10,000": 10000, "Rs 10,000-30,000": 30000, "Above Rs 30,000": 60000}


def _has(text: str, kw: str) -> bool:
    if re.match(r"^[a-z0-9 .\-]+$", kw):
        return re.search(rf"(?<![a-z]){re.escape(kw)}(?![a-z])", text) is not None
    return kw in text


def extract(message: str, expecting: str | None) -> dict:
    """Pull every slot value we can find in one message."""
    text = message.strip().lower()
    found: dict = {}

    # business type: exact dataset business types first, then segment keywords
    for bt, seg in sorted(business_types().items(), key=lambda kv: -len(kv[0])):
        if bt.lower() in text:
            found.update(business_type=bt, segment=seg)
            break
    if "segment" not in found:
        for seg in ["mfg", "multi", "prof", "micro"]:
            if any(_has(text, k) for k in SEGMENT_KEYWORDS[seg]):
                hits = [k for k in SEGMENT_KEYWORDS[seg] if _has(text, k)]
                kw = next((k for k in hits if k in KEYWORD_TYPE), hits[0])
                found.update(segment=seg, business_type=found.get("business_type") or KEYWORD_TYPE.get(kw, GENERIC_TYPE[seg]))
                break

    for city in sorted(city_tiers(), key=len):
        if re.search(rf"(?<![a-z]){city.lower()}(?![a-z])", text):
            found["city"] = city
    for alias, city in CITY_ALIASES.items():
        if alias.rstrip("்") in text:  # Tamil case endings drop the final virama (கோயம்புத்தூரில்)
            found["city"] = city

    m = re.search(r"(\d+)\s*\+?\s*(staff|employees|people|workers|team|log|लोग|कर्मचारी|ஊழியர்|பேர்)", text)
    if m:
        found["employees"] = int(m.group(1))
    m = re.search(r"(\d+)\s*(branches|branch|sites|site|outlets|stores|shops|locations|offices|office|clinics|clinic|शाखा|दुकानें|கிளை|கடைகள்)", text)
    if m:
        found["sites"] = int(m.group(1))

    for value, kws in INTERNET_KEYWORDS.items():
        if any(_has(text, k) for k in kws):
            found["current_internet"] = value
            break

    # Phrases like "backup internet" belong to failover, not to data backup.
    need_text = re.sub(r"backup internet|बैकअप इंटरनेट", " failover ", text)
    needs = [n for n, kws in NEED_KEYWORDS.items() if any(_has(need_text, k) for k in kws)]
    if needs:
        found["needs"] = needs

    g = re.search(r"\b[0-9]{2}[a-z]{5}[0-9]{4}[a-z][0-9a-z]z[0-9a-z]\b", text)
    if g:
        found.update(gstin=normalise_gstin(g.group(0)), has_gstin=True)
    u = re.search(r"udyam[\s\-]*[a-z]{2}[\s\-]*\d{2}[\s\-]*\d{7}", text)
    if u:
        found.update(udyam_number=normalise_udyam(u.group(0)), has_udyam=True)

    m = re.search(r"(?:(?<![a-z])rs\.?|₹|(?<![a-z])inr|budget)\s*(\d[\d,]*)\s*(k\b)?", text) or \
        re.search(r"(\d[\d,]*)\s*(k\b)?\s*(?:rupees|(?<![a-z])rs\b|₹|रुपये|ரூபாய்)", text)
    if m:
        val = int(m.group(1).replace(",", "")) * (1000 if m.group(2) else 1)
        if val >= 300:
            found["budget"] = val

    # A bare answer to the question we just asked.
    if expecting in RANGE_MAP or message.strip() in RANGE_MAP:
        if message.strip() in RANGE_MAP and expecting in ("employees", "sites", "budget"):
            found[expecting] = RANGE_MAP[message.strip()]
    if expecting in ("employees", "sites") and expecting not in found:
        n = re.fullmatch(r"\s*(\d{1,4})\s*", text)
        if n:
            found[expecting] = int(n.group(1))
    if expecting == "budget" and "budget" not in found:
        n = re.fullmatch(r"\s*([\d,]{3,7})\s*", text)
        if n:
            found["budget"] = int(n.group(1).replace(",", ""))
        elif any(w in text for w in ["not sure", "pata nahi", "पता नहीं", "தெரியாது"]):
            found["budget"] = None
            found["budget_skipped"] = True
    if expecting == "gstin" and "gstin" not in found:
        if any(_has(text, w) for w in NO):
            found["has_gstin"] = False
        elif any(_has(text, w) for w in YES):
            found["has_gstin"] = True
    if expecting == "needs" and text in ("none", "nothing else", "no", "बस", "இல்லை"):
        found["needs_done"] = True
    return found


def _llm_fallback(message: str, expecting: str | None) -> dict:
    allowed = {"segment": ["micro", "prof", "multi", "mfg"], "city": sorted(city_tiers()),
               "employees": "integer", "sites": "integer", "current_internet": list(INTERNET_KEYWORDS),
               "needs": list(NEED_KEYWORDS), "has_gstin": "boolean", "budget": "integer rupees per month"}
    raw = llm.extract_slots(message, allowed)
    clean = {}
    if raw.get("segment") in allowed["segment"]:
        clean["segment"] = raw["segment"]
        clean["business_type"] = GENERIC_TYPE[raw["segment"]]
    if raw.get("city") in city_tiers():
        clean["city"] = raw["city"]
    for k in ("employees", "sites", "budget"):
        if isinstance(raw.get(k), int) and 0 < raw[k] < 10_000_000:
            clean[k] = raw[k]
    if raw.get("current_internet") in INTERNET_KEYWORDS:
        clean["current_internet"] = raw["current_internet"]
    if isinstance(raw.get("needs"), list):
        clean["needs"] = [n for n in raw["needs"] if n in NEED_KEYWORDS]
    if isinstance(raw.get("has_gstin"), bool):
        clean["has_gstin"] = raw["has_gstin"]
    return clean


def merge(profile: dict, found: dict, expecting: str | None = None) -> dict:
    p = dict(profile)
    if p.get("segment") and expecting != "business_type":
        # "CCTV in every store" must not turn a retail chain into a single shop.
        found = {k: v for k, v in found.items() if k not in ("segment", "business_type")}
    for k, val in found.items():
        if k == "needs":
            p["needs"] = list(dict.fromkeys((p.get("needs") or []) + val))
            p["needs_asked"] = True
        else:
            p[k] = val
    if p.get("segment") == "micro" and "sites" not in p:
        p["sites"] = 1
    if p.get("city") in city_tiers():
        p["city_tier"] = city_tiers()[p["city"]]["tier"]
        p["state"] = city_tiers()[p["city"]]["state"]
    if p.get("gstin"):
        p["gstin_status"] = lookup_gstin(p["gstin"])["status"]
    return p


def next_slot(p: dict) -> str | None:
    if not p.get("segment"):
        return "business_type"
    if not p.get("city"):
        return "city"
    if not p.get("employees"):
        return "employees"
    if not p.get("sites"):
        return "sites"
    if not p.get("current_internet"):
        return "current_internet"
    if not p.get("needs_asked"):
        return "needs"
    if "has_gstin" not in p:
        return "gstin"
    if "budget" not in p and not p.get("budget_skipped"):
        return "budget"
    return None


def turn(profile: dict, message: str, expecting: str | None, language: str = "en") -> dict:
    found = extract(message, expecting)
    if expecting == "needs" and not found.get("needs"):
        found.setdefault("needs", [])
    if not found and llm.enabled():
        found = _llm_fallback(message, expecting)
    understood = bool(found)
    profile = merge(profile, found, expecting)
    slot = next_slot(profile)
    return {
        "profile": profile, "understood": understood, "extracted": found, "next": slot,
        "chips": CHIPS.get(slot, []), "done": slot is None,
        "gstin_status": profile.get("gstin_status"),
    }
