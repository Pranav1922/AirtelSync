"""Business analytics over smb_leads.csv plus live prototype activity, and an explainable lead score."""
from __future__ import annotations

import math
from functools import lru_cache

import pandas as pd

from .data import gstin_registry, leads

FUNNEL = [("Lead", None), ("Contacted", "reached_contacted"), ("Needs assessed", "reached_needs_assessed"),
          ("Quote accepted", "reached_quote_accepted"), ("KYC complete", "reached_kyc_complete"),
          ("Activated", "reached_activated")]

# How the digital journey addresses each observed drop reason.
DROP_LEVERS = {
    "Unreachable after 3 attempts": ("partial", "Self-serve advisor link + WhatsApp nudge instead of cold calls"),
    "Wrong or invalid number": ("no", "Data quality at lead capture (OTP-verified forms)"),
    "Not interested on first call": ("no", "Out of scope"),
    "Owner had no time for a visit": ("yes", "No visit needed: 5-minute advisor on the phone"),
    "Visit not scheduled by sales": ("yes", "No visit needed: advisor recommends instantly"),
    "Locked in with current provider": ("no", "Out of scope (contract timing campaigns)"),
    "Only wanted a mobile plan": ("no", "Sell the mobile plan; nurture for bundle later"),
    "Price too high": ("partial", "Essential tier, budget-aware recommendation, transparent range"),
    "Competitor offered cheaper plan": ("partial", "Transparent all-in monthly price"),
    "Quote too complex to understand": ("yes", "Plain-language quote with reasons per product"),
    "Quote took too long to arrive": ("yes", "Instant quote from the catalogue"),
    "Decided to wait": ("partial", "Saved quote + reminder"),
    "Missing GST or Udyam document": ("yes", "Registry lookup by number; upload later"),
    "Found paperwork too long": ("yes", "4 uploads with instant OCR checks"),
    "Document details did not match": ("yes", "Mismatch flagged instantly with the reason"),
    "Authorised signatory not available": ("partial", "Remote upload by signatory; e-sign in a later phase"),
    "Installation delayed beyond 21 days": ("partial", "Install-day estimate up front + live tracker"),
    "Customer cancelled before install": ("partial", "Live tracker reduces uncertainty"),
    "Site not feasible for fibre": ("partial", "5G AirFiber alternative offered in catalogue"),
    "First payment failed": ("partial", "Pay setup on first bill option"),
}


def _stats(g: pd.DataFrame) -> dict:
    n, act = len(g), int(g.reached_activated.sum())
    a = g[g.reached_activated]
    return {
        "leads": n, "activated": act, "conversion_pct": round(act / n * 100, 1) if n else 0,
        "blended_cac": round(g.acquisition_cost_inr.sum() / act) if act else None,
        "acquisition_spend": int(g.acquisition_cost_inr.sum()),
        "median_bundle_inr": float(a.monthly_bundle_value_inr.median()) if act else None,
        "mean_bundle_inr": round(float(a.monthly_bundle_value_inr.mean())) if act else None,
        "days_to_activate": round(float(a.days_lead_to_activation.mean()), 1) if act else None,
        "churn_6m_pct": round(float((a.churned_within_6_months == "Y").mean()) * 100, 1) if act else None,
        "nps_mean": round(float(a.nps_score.mean()), 1) if act else None,
        "follow_up_calls": round(float(a.customer_follow_up_calls.mean()), 1) if act else None,
        "needs_to_quote_pct": round(float(g.reached_quote_accepted.sum() / max(g.reached_needs_assessed.sum(), 1)) * 100, 1),
    }


@lru_cache(maxsize=1)
def overview() -> dict:
    df = leads()
    funnel, prev = [], len(df)
    for name, col in FUNNEL:
        n = len(df) if col is None else int(df[col].sum())
        funnel.append({"stage": name, "count": n, "pct_of_previous": round(n / prev * 100, 1), "pct_of_leads": round(n / len(df) * 100, 1)})
        prev = n
    dims = {d: [{"key": str(k), **_stats(g)} for k, g in df.groupby(d)]
            for d in ["segment", "lead_source", "city_tier", "has_gstin", "has_udyam", "current_internet", "annual_turnover_band"]}
    drops = []
    for (stage, reason), g in df[df.outcome == "Dropped"].groupby(["stage_reached", "drop_reason"]):
        lever = DROP_LEVERS.get(reason, ("no", ""))
        drops.append({"stage": stage, "reason": reason, "count": len(g), "addressable": lever[0], "lever": lever[1],
                      "acquisition_spend": int(g.acquisition_cost_inr.sum())})
    drops.sort(key=lambda d: -d["count"])
    act = df[df.reached_activated]
    reg = gstin_registry()
    status = act.gstin.map(lambda g: reg.get(g, {}).get("status") if isinstance(g, str) else None)
    return {
        "totals": _stats(df), "funnel": funnel, "dimensions": dims, "drop_reasons": drops,
        "mean_cac_activated_only": round(float(act.acquisition_cost_inr.mean())),
        "compliance": {
            "activated_with_inactive_gstin": int(status.isin(["Cancelled", "Suspended"]).sum()),
            "activated_without_gstin": int((act.has_gstin == "N").sum()),
        },
        "period": {"from": df.created_date.min(), "to": df.created_date.max()},
        "historical_violations": historical_violations(),
        "addressable_drops": sum(d["count"] for d in drops if d["addressable"] == "yes"),
        "partially_addressable_drops": sum(d["count"] for d in drops if d["addressable"] == "partial"),
    }


@lru_cache(maxsize=1)
def historical_violations() -> dict:
    """Re-check every activated bundle against today's catalogue rules: what manual selling let through."""
    from collections import Counter
    from .recommend import resolve_profile, validate_bundle
    df = leads()
    counts, bundles = Counter(), 0
    for r in df[df.reached_activated].to_dict("records"):
        items = {x.split("x")[0]: int(x.split("x")[1]) for x in r["bundle_products"].split(";")}
        p = resolve_profile({"segment": r["segment_code"], "employees": r["employee_count"], "sites": r["num_sites"],
                             "city_tier": r["city_tier"], "gstin": r["gstin"] if isinstance(r["gstin"], str) else None,
                             "has_gstin": r["has_gstin"] == "Y"})
        errs = validate_bundle(items, p)
        bundles += bool(errs)
        for e in errs:
            msg = e["message"]
            kind = "No active GSTIN" if "GSTIN" in msg else "City tier" if "tier" in msg else \
                "Below minimum size" if "at least" in msg else "Missing dependency" if e["rule"] == "dependency" else e["rule"]
            counts[(kind, e["product_id"])] += 1
    return {"bundles_with_violations": bundles, "activated": int(df.reached_activated.sum()),
            "items": [{"rule": k, "product_id": pid, "count": n} for (k, pid), n in counts.most_common()]}


# ------------------------------------------------------------------ explainable lead score

SCORE_FEATURES = {
    "segment": "Segment", "lead_source": "Lead source", "gst_state": "GSTIN status", "has_udyam": "Udyam registered",
    "current_internet": "Current internet", "annual_turnover_band": "Turnover band", "city_tier": "City tier",
}
# Deliberately excluded: preferred_language, contact name/role, state/city (proxies for community or region).


def _features(df: pd.DataFrame) -> pd.DataFrame:
    reg = gstin_registry()
    f = df[["segment", "lead_source", "has_udyam", "annual_turnover_band", "city_tier"]].astype(str).copy()
    f["current_internet"] = df.current_internet.fillna("Unknown")
    f["gst_state"] = df.gstin.map(lambda g: reg.get(g, {}).get("status", "Unknown") if isinstance(g, str) else "No GSTIN")
    return f


@lru_cache(maxsize=1)
def score_model() -> dict:
    """Naive-Bayes style log-odds per feature value with Laplace smoothing.
    Trained on Apr-May 2026 leads, checked on June 2026 leads (time split)."""
    df = leads()
    train = df[df.created_date < "2026-06-01"]
    test = df[df.created_date >= "2026-06-01"]
    model = _fit(_features(train), train.reached_activated)
    auc = _auc(_score_frame(model, _features(test)), test.reached_activated)
    full = _fit(_features(df), df.reached_activated)
    full["backtest"] = {"train": "Apr-May 2026", "test": "Jun 2026", "test_leads": len(test), "auc": round(auc, 3),
                        "note": "Retrospective check on synthetic data. June leads created late in the month may not "
                                "have had time to activate. Not a validated predictive model."}
    return full


def _fit(f: pd.DataFrame, y: pd.Series) -> dict:
    pos, neg = y.sum(), (~y).sum()
    prior = math.log((pos + 1) / (neg + 1))
    weights = {}
    for col in SCORE_FEATURES:
        w = {}
        for val, g in y.groupby(f[col]):
            p1 = (g.sum() + 1) / (pos + 2)
            p0 = ((~g).sum() + 1) / (neg + 2)
            w[str(val)] = round(math.log(p1 / p0), 3)
        weights[col] = w
    # Compliance guardrail: history contains activations on cancelled/suspended GSTINs (a process leak).
    # The score must never reward that, so those values can only lower priority.
    for val in ("Cancelled", "Suspended"):
        if val in weights["gst_state"]:
            weights["gst_state"][val] = min(weights["gst_state"][val], weights["gst_state"].get("No GSTIN", 0.0))
    return {"prior": prior, "weights": weights}


def _score_frame(model: dict, f: pd.DataFrame) -> pd.Series:
    s = pd.Series(model["prior"], index=f.index)
    for col in SCORE_FEATURES:
        s = s + f[col].map(model["weights"][col]).fillna(0)
    return s


def _auc(score: pd.Series, y: pd.Series) -> float:
    r = score.rank()
    pos = y.sum()
    neg = len(y) - pos
    return float((r[y].sum() - pos * (pos + 1) / 2) / (pos * neg)) if pos and neg else float("nan")


def explain_score(row: dict) -> dict:
    m = score_model()
    f = _features(pd.DataFrame([row]))
    contrib = []
    total = m["prior"]
    for col, label in SCORE_FEATURES.items():
        val = str(f.iloc[0][col])
        w = m["weights"][col].get(val, 0.0)
        total += w
        contrib.append({"feature": label, "value": val, "points": round(w * 10, 1)})
    prob = 1 / (1 + math.exp(-total))
    contrib.sort(key=lambda c: -abs(c["points"]))
    return {"propensity": round(prob, 3), "contributions": contrib}


NEXT_ACTION = {
    "yes": "Send the SYNC advisor link on WhatsApp with a pre-filled profile",
    "partial": "Partner or field call with the Essential bundle and the transparent price range",
}


@lru_cache(maxsize=1)
def priority_queue(limit: int = 60) -> list[dict]:
    """Dropped leads worth re-engaging, ranked by propensity x opportunity x recoverability."""
    df = leads()
    m = score_model()
    seg_value = df[df.reached_activated].groupby("segment").monthly_bundle_value_inr.median().to_dict()
    cand = df[(df.outcome == "Dropped") & df.drop_reason.map(lambda r: DROP_LEVERS.get(r, ("no",))[0] in ("yes", "partial"))].copy()
    cand["logit"] = _score_frame(m, _features(cand))
    cand["prob"] = 1 / (1 + (-cand.logit).map(math.exp))
    cand["recover"] = cand.drop_reason.map(lambda r: 1.0 if DROP_LEVERS[r][0] == "yes" else 0.5)
    stage_w = {"Lead": 0.6, "Contacted": 0.8, "Needs assessed": 1.0, "Quote accepted": 1.2, "KYC complete": 1.3}
    cand["warmth"] = cand.stage_reached.map(stage_w).fillna(1.0)
    cand["opportunity"] = cand.segment.map(seg_value)
    cand["priority"] = cand.prob * cand.recover * cand.warmth * cand.opportunity
    top = cand.sort_values("priority", ascending=False).head(limit)
    pmax = float(top.priority.max())
    out = []
    for r in top.to_dict("records"):
        lever = DROP_LEVERS[r["drop_reason"]]
        owner = "Channel partner" if r["lead_source"] == "Channel partner" else \
            "Field sales" if r["segment"] in ("Small multi-site businesses", "Small manufacturers") else "Digital nudge"
        out.append({
            "lead_id": r["lead_id"], "business_name": r["business_name"], "segment": r["segment"], "city": r["city"],
            "lead_source": r["lead_source"], "stage_reached": r["stage_reached"], "drop_reason": r["drop_reason"],
            "priority_score": round(r["priority"] / pmax * 100), "propensity": round(r["prob"], 3),
            "opportunity_inr": r["opportunity"], "owner": owner,
            "compliance_hold": r["gstin"] in gstin_registry() and gstin_registry()[r["gstin"]]["status"] != "Active"
                               if isinstance(r["gstin"], str) else False,
            "next_action": f"{NEXT_ACTION[lever[0]]}. {lever[1]}.",
            "why": explain_score(r)["contributions"][:4]
                   + [{"feature": "Stage reached", "value": r["stage_reached"], "points": round(math.log(r["warmth"]) * 10, 1)},
                      {"feature": "Drop reason recoverable", "value": lever[0], "points": round(math.log(r["recover"]) * 10, 1)}],
        })
    return out
