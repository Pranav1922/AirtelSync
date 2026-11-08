"""Deterministic, explainable bundle recommendation engine.

All products, prices and rules come from product_catalogue.csv. Essential / Growth /
Advanced are groupings of real catalogue IDs, never invented products.
"""
from __future__ import annotations

import math
from collections import Counter
from functools import lru_cache

from .data import SEGMENT_NAMES, Product, catalogue, city_tiers, leads
from .kyc.validators import lookup_gstin

# Need -> catalogue product that fulfils it.
NEED_PRODUCT = {
    "mobile": None,  # P07 or P08, chosen by segment
    "failover": "P09", "whatsapp": "P15", "sms": "P14", "tollfree": "P13", "telephony": "P12",
    "email": "P16", "data_backup": "P17", "website": "P18", "pos": "P19", "endpoint": "P20",
    "firewall": "P21", "wifi": "P22", "cctv": "P23", "iot": "P24", "fleet": "P25",
    "multisite_mgmt": "P10", "static_ip": "P11",
}
NEED_LABEL = {
    "internet": "reliable internet", "mobile": "business mobile lines", "failover": "backup internet when the main line fails",
    "whatsapp": "WhatsApp to reach customers", "sms": "SMS alerts and promotions", "tollfree": "a toll-free number",
    "telephony": "a business phone system", "email": "business email on your own domain", "data_backup": "automatic data backup",
    "website": "a website", "pos": "billing and UPI/card acceptance", "endpoint": "virus and ransomware protection",
    "firewall": "a managed firewall", "wifi": "secure Wi-Fi with a guest network", "cctv": "CCTV you can watch on your phone",
    "iot": "machine monitoring", "fleet": "vehicle tracking", "multisite_mgmt": "central management of all your sites",
    "static_ip": "a fixed IP for CCTV or remote access",
}
# Connectivity preference per segment and level, with fallbacks when a product is not eligible.
CONNECTIVITY = {
    "micro": {"essential": ["P04", "P01"], "growth": ["P01", "P04"], "advanced": ["P01", "P04"]},
    "prof": {"essential": ["P01", "P04"], "growth": ["P02", "P01"], "advanced": ["P03", "P02", "P01"]},
    "multi": {"essential": ["P01"], "growth": ["P02", "P01"], "advanced": ["P02", "P01"]},
    "mfg": {"essential": ["P03", "P02", "P01"], "growth": ["P05", "P03", "P02"], "advanced": ["P06", "P05", "P03", "P02"]},
}
# Add-ons each level layers on top of what the owner asked for (informed by historical attach rates).
SEGMENT_ADDONS = {
    "micro": {"growth": ["wifi", "cctv"], "advanced": ["wifi", "cctv", "website", "sms"]},
    "prof": {"growth": ["email", "endpoint", "data_backup"], "advanced": ["email", "endpoint", "data_backup", "failover", "firewall"]},
    "multi": {"growth": ["cctv", "failover"], "advanced": ["cctv", "failover", "multisite_mgmt", "firewall", "tollfree"]},
    "mfg": {"growth": ["email", "endpoint", "cctv"], "advanced": ["email", "endpoint", "cctv", "iot", "firewall", "static_ip"]},
}
LEVELS = ["essential", "growth", "advanced"]
LEVEL_PITCH = {
    "essential": "Covers everything you asked for at the lowest catalogue price.",
    "growth": "Adds the tools similar businesses most often add once they are online.",
    "advanced": "Adds backup, security and central control for zero-downtime operations.",
}


# ---------------------------------------------------------------- eligibility

def resolve_profile(profile: dict) -> dict:
    """Fill derived fields: city tier, GSTIN registry status. Never mutates the input."""
    p = dict(profile)
    p["employees"] = max(1, int(p.get("employees") or 1))
    p["sites"] = max(1, int(p.get("sites") or 1))
    city = city_tiers().get(p.get("city") or "")
    if city and not p.get("city_tier"):
        p["city_tier"], p["state"] = city["tier"], city["state"]
    p["city_tier"] = int(p.get("city_tier") or 2)
    p["needs"] = list(dict.fromkeys(p.get("needs") or []))
    if p.get("gstin"):
        res = lookup_gstin(p["gstin"])
        p["gstin_status"] = res["status"]
    elif p.get("has_gstin"):
        p["gstin_status"] = "unverified"  # owner says they have one; checked at KYC
    else:
        p["gstin_status"] = "none"
    return p


def gstin_ok(p: dict) -> bool:
    return p.get("gstin_status") in ("active", "unverified")


def product_eligibility(prod: Product, p: dict) -> list[str]:
    """Reasons a product cannot be sold to this profile (empty list = eligible).
    Dependencies are bundle-level and checked in validate_bundle()."""
    why = []
    if p["city_tier"] not in prod.city_tiers:
        why.append(f"{prod.name} is only sold in tier {'/'.join(map(str, sorted(prod.city_tiers)))} cities.")
    if p["employees"] < prod.min_employees:
        why.append(f"{prod.name} needs at least {prod.min_employees} employees.")
    if p["sites"] < prod.min_sites:
        why.append(f"{prod.name} needs at least {prod.min_sites} sites.")
    if prod.requires_gstin and not gstin_ok(p):
        status = p.get("gstin_status")
        why.append(f"{prod.name} needs an active GSTIN" + (f" (registry status: {status})." if status not in (None, "none") else "."))
    return why


def validate_bundle(items: dict[str, int], p: dict) -> list[dict]:
    """Backend-enforced bundle rules: eligibility, dependencies, quantities."""
    cat = catalogue()
    errors = []
    for pid, qty in items.items():
        prod = cat.get(pid)
        if prod is None:
            errors.append({"product_id": pid, "rule": "unknown", "message": f"{pid} is not in the catalogue."})
            continue
        if not isinstance(qty, int) or qty < 1 or qty > 500:
            errors.append({"product_id": pid, "rule": "quantity", "message": f"Quantity for {prod.name} must be 1-500."})
        for msg in product_eligibility(prod, p):
            errors.append({"product_id": pid, "rule": "eligibility", "message": msg})
        if prod.requires_one_of and not (prod.requires_one_of & items.keys()):
            names = ", ".join(cat[x].name for x in sorted(prod.requires_one_of))
            errors.append({"product_id": pid, "rule": "dependency", "requires_one_of": sorted(prod.requires_one_of),
                           "message": f"{prod.name} works only with one of: {names}."})
    return errors


# ---------------------------------------------------------------- quantities

def suggested_quantity(pid: str, p: dict) -> int:
    """Quantities follow the median ratios in historical activated bundles (see docs/PRODUCT_DECISIONS.md)."""
    unit = catalogue()[pid].unit
    seg, emp, sites = p.get("segment"), p["employees"], p["sites"]
    small = seg in ("multi", "mfg")
    if unit in ("per site", "per counter"):
        return sites
    if unit == "per line":
        if seg == "micro":
            return min(2, emp)
        return max(2, math.ceil(emp * (0.06 if small else 0.2)))
    if unit == "per user":
        return min(emp, 2) if seg == "micro" else max(2, math.ceil(emp * (0.15 if small else 0.6)))
    if unit == "per device":
        if pid == "P24":
            return max(4, math.ceil(emp * 0.12))
        return 2 if seg == "micro" else max(2, math.ceil(emp * (0.12 if small else 0.5)))
    if unit == "per camera":
        return {"micro": 2, "prof": 2, "multi": 2 * sites, "mfg": 4 * sites}.get(seg, 2)
    if unit == "per channel":
        return max(2, math.ceil(emp * 0.2))
    if unit == "per vehicle":
        return max(2, math.ceil(emp * 0.08))
    return 1


# ---------------------------------------------------------------- evidence from history

@lru_cache(maxsize=1)
def attach_rates() -> dict[str, dict[str, float]]:
    """Share of activated customers in each segment whose bundle included each product."""
    df = leads()
    act = df[df.outcome == "Activated"]
    out = {}
    for seg, grp in act.groupby("segment_code"):
        c = Counter(x.split("x")[0] for b in grp.bundle_products for x in b.split(";"))
        out[seg] = {pid: n / len(grp) for pid, n in c.items()}
    return out


def mobile_product(p: dict) -> str:
    return "P07" if p.get("segment") == "micro" else "P08"


# ---------------------------------------------------------------- recommendation

def _pick(candidates: list[str], p: dict, notes: list[str]) -> str | None:
    cat = catalogue()
    for pid in candidates:
        why = product_eligibility(cat[pid], p)
        if not why:
            return pid
        notes.append(why[0])
    return None


def _need_pid(need: str, p: dict) -> str | None:
    return mobile_product(p) if need == "mobile" else NEED_PRODUCT.get(need)


def build_level(level: str, p: dict) -> dict:
    cat = catalogue()
    seg = p.get("segment") or "micro"
    notes: list[str] = []
    items: dict[str, dict] = {}

    def add(pid: str, reason: str):
        if pid in items:
            items[pid]["reasons"].append(reason)
            return
        why = product_eligibility(cat[pid], p)
        if why:
            notes.append(why[0])
            return
        items[pid] = {"product_id": pid, "quantity": suggested_quantity(pid, p), "reasons": [reason]}

    conn = _pick(CONNECTIVITY[seg][level], p, notes)
    if conn:
        reason = f"Main internet line for {p['sites']} site{'s' if p['sites'] > 1 else ''}"
        if p.get("current_internet") in ("Mobile hotspot", "Home broadband"):
            reason += f", replacing your current {p['current_internet'].lower()}"
        add(conn, reason + ".")
    add(mobile_product(p), "Business mobile lines for the team, on one bill with your internet.")

    for need in p["needs"]:
        if need == "internet":
            continue
        pid = _need_pid(need, p)
        if pid:
            add(pid, f"You asked for {NEED_LABEL.get(need, need)}.")
        if need == "firewall" and pid and pid not in items:
            add("P20", "Managed firewall needs 10+ staff and an active GSTIN, so device protection covers you instead.")

    if level != "essential":
        rates = attach_rates().get(seg, {})
        for need in SEGMENT_ADDONS[seg][level]:
            pid = _need_pid(need, p)
            if pid and pid not in items:
                share = rates.get(pid)
                ev = f" {round(share * 100)}% of similar businesses that activated with us chose it." if share else ""
                add(pid, f"Recommended for {SEGMENT_NAMES[seg].lower()}: {NEED_LABEL[need]}.{ev}")

    # Satisfy dependencies (e.g. Static IP needs fibre) by dropping what cannot be supported.
    chosen = {k: v["quantity"] for k, v in items.items()}
    for err in validate_bundle(chosen, p):
        if err["rule"] == "dependency" and err["product_id"] in items:
            notes.append(err["message"])
            items.pop(err["product_id"])
    return {"level": level, "pitch": LEVEL_PITCH[level], "items": list(items.values()),
            "notes": list(dict.fromkeys(notes))}


def recommend(profile: dict) -> dict:
    from .quote import price_items  # local import avoids a cycle

    p = resolve_profile(profile)
    options = []
    for level in LEVELS:
        opt = build_level(level, p)
        opt["pricing"] = price_items({i["product_id"]: i["quantity"] for i in opt["items"]})
        options.append(opt)

    # Drop levels identical to the one below (small businesses may not qualify for more).
    unique = []
    for o in options:
        ids = {i["product_id"]: i["quantity"] for i in o["items"]}
        if not unique or ids != {i["product_id"]: i["quantity"] for i in unique[-1]["items"]}:
            unique.append(o)

    budget = profile.get("budget")
    recommended = unique[min(1, len(unique) - 1)]["level"]
    budget_note = None
    if budget:
        # Never upsell to the ceiling of the budget: Growth at most, lower if it does not fit.
        within = [o for o in unique[:2] if o["pricing"]["monthly_min"] <= budget]
        if within:
            recommended = within[-1]["level"]
        else:
            recommended = unique[0]["level"]
            over = unique[0]["pricing"]["monthly_min"] - budget
            budget_note = (f"Even the Essential bundle is Rs {over:,} above your Rs {budget:,} monthly budget. "
                           "Remove optional items in the quote to bring it down.")
    return {"profile": public_profile(p), "options": unique, "recommended": recommended, "budget_note": budget_note}


def public_profile(p: dict) -> dict:
    from .kyc.validators import mask_id
    out = {k: v for k, v in p.items() if k not in ("gstin", "udyam_number")}
    out["gstin_masked"] = mask_id(p.get("gstin"))
    out["segment_name"] = SEGMENT_NAMES.get(p.get("segment"), "")
    return out
