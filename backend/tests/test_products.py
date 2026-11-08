import pytest

from app.data import catalogue
from app.quote import price_items
from app.recommend import product_eligibility, recommend, resolve_profile, suggested_quantity, validate_bundle


def prof(**kw):
    base = {"segment": "prof", "employees": 12, "sites": 1, "city": "Mumbai", "has_gstin": True, "needs": []}
    return resolve_profile({**base, **kw})


def test_catalogue_loads_all_25_products_from_csv():
    cat = catalogue()
    assert len(cat) == 25
    p05 = cat["P05"]
    assert (p05.price_min, p05.price_max, p05.setup_fee, p05.min_employees, p05.install_days) == (8000, 12000, 10000, 10, 21)
    assert cat["P09"].requires_one_of == {"P01", "P02", "P03", "P05", "P06"}
    assert cat["P03"].city_tiers == {1}


def test_price_is_catalogue_price_times_quantity_with_no_discount():
    q = price_items({"P01": 2, "P07": 3, "P23": 4})
    assert q["monthly_min"] == 999 * 2 + 299 * 3 + 199 * 4
    assert q["monthly_max"] == 1199 * 2 + 399 * 3 + 299 * 4
    assert q["setup_total"] == 1800 * 4
    assert q["first_bill_min"] == q["monthly_min"] + q["setup_total"]
    assert q["longest_commitment_months"] == 12
    assert q["contract_value_min"] == 999 * 2 * 12 + 299 * 3 * 1 + 199 * 4 * 12 + 7200


def test_install_days_is_slowest_product():
    assert price_items({"P07": 1, "P05": 1, "P23": 1})["install_days"] == 21


def test_gstin_required_products_blocked_without_gstin():
    p = prof(has_gstin=False)
    assert product_eligibility(catalogue()["P15"], p)
    assert not product_eligibility(catalogue()["P16"], p)


def test_gstin_required_products_blocked_for_cancelled_and_suspended_gstin():
    cancelled = prof(gstin="37IHKXV5167L1ZS")
    assert cancelled["gstin_status"] == "cancelled"
    assert "cancelled" in product_eligibility(catalogue()["P12"], cancelled)[0]
    from app.data import gstin_registry
    suspended = next(g for g, r in gstin_registry().items() if r["status"] == "Suspended")
    assert product_eligibility(catalogue()["P13"], prof(gstin=suspended))


def test_employee_site_and_tier_limits():
    cat = catalogue()
    assert product_eligibility(cat["P06"], prof(employees=24))
    assert not product_eligibility(cat["P06"], prof(employees=25))
    assert product_eligibility(cat["P10"], prof(employees=40, sites=2))
    assert not product_eligibility(cat["P10"], prof(employees=40, sites=3))
    assert product_eligibility(cat["P03"], prof(city="Nagpur"))  # tier 2
    assert not product_eligibility(cat["P03"], prof(city="Mumbai"))


def test_dependencies_enforced_on_backend():
    p = prof()
    errs = validate_bundle({"P09": 1, "P07": 1}, p)
    assert any(e["rule"] == "dependency" and e["product_id"] == "P09" for e in errs)
    assert not validate_bundle({"P09": 1, "P02": 1}, p)
    assert any(e["rule"] == "dependency" for e in validate_bundle({"P11": 1, "P05": 1}, p))  # Static IP needs fibre


def test_quantity_bounds_and_unknown_products():
    p = prof()
    assert any(e["rule"] == "quantity" for e in validate_bundle({"P01": 0}, p))
    assert any(e["rule"] == "unknown" for e in validate_bundle({"P99": 1}, p))


def test_suggested_quantities_scale_with_business():
    multi = resolve_profile({"segment": "multi", "employees": 44, "sites": 11, "city": "Pune"})
    assert suggested_quantity("P02", multi) == 11
    assert suggested_quantity("P23", multi) == 22
    assert suggested_quantity("P16", prof(employees=10)) == 6


@pytest.mark.parametrize("profile", [
    {"segment": "micro", "employees": 3, "sites": 1, "city": "Ludhiana", "needs": ["pos", "whatsapp"]},
    {"segment": "prof", "employees": 14, "sites": 1, "city": "Kochi", "needs": ["email"], "gstin": "32TTNXB7384T1ZW"},
    {"segment": "multi", "employees": 60, "sites": 8, "city": "Pune", "needs": ["cctv", "failover"], "has_gstin": True},
    {"segment": "mfg", "employees": 85, "sites": 1, "city": "Nagpur", "needs": ["iot"], "gstin": "27XUIXG0767D1ZP"},
])
def test_every_recommended_bundle_is_valid_and_uses_catalogue_ids(profile):
    rec = recommend(profile)
    p = resolve_profile(profile)
    for opt in rec["options"]:
        items = {i["product_id"]: i["quantity"] for i in opt["items"]}
        assert items and set(items) <= set(catalogue())
        assert validate_bundle(items, p) == []
        assert all(i["reasons"] for i in opt["items"])
        assert opt["pricing"]["monthly_min"] == price_items(items)["monthly_min"]
    totals = [o["pricing"]["monthly_min"] for o in rec["options"]]
    assert totals == sorted(totals)


def test_micro_without_gstin_gets_no_gstin_products():
    rec = recommend({"segment": "micro", "employees": 2, "city": "Patna", "has_gstin": False, "needs": ["whatsapp", "pos"]})
    for opt in rec["options"]:
        assert not any(catalogue()[i["product_id"]].requires_gstin for i in opt["items"])
    assert any("WhatsApp" in n for n in rec["options"][0]["notes"])


def test_budget_picks_highest_level_that_fits():
    profile = {"segment": "prof", "employees": 5, "sites": 1, "city": "Kolkata", "has_gstin": True, "needs": ["email"]}
    rec = recommend({**profile, "budget": 10**6})
    assert rec["recommended"] == "growth"  # no upsell to the budget ceiling
    rec = recommend({**profile, "budget": 500})
    assert rec["recommended"] == "essential" and rec["budget_note"]
