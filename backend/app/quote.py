"""Transparent pricing. Every number is catalogue price x quantity. No discounts are applied."""
from __future__ import annotations

from .data import catalogue


def price_items(items: dict[str, int]) -> dict:
    cat = catalogue()
    lines = []
    for pid, qty in items.items():
        prod = cat[pid]
        lines.append({
            "product_id": pid, "name": prod.name, "category": prod.category, "unit": prod.unit,
            "quantity": qty, "unit_price_min": prod.price_min, "unit_price_max": prod.price_max,
            "monthly_min": prod.price_min * qty, "monthly_max": prod.price_max * qty,
            "setup": prod.setup_fee * qty, "contract_months": prod.min_contract_months,
            "install_days": prod.install_days,
        })
    monthly_min = sum(line["monthly_min"] for line in lines)
    monthly_max = sum(line["monthly_max"] for line in lines)
    setup = sum(line["setup"] for line in lines)
    commitment = max((line["contract_months"] for line in lines), default=0)
    install = max((line["install_days"] for line in lines), default=0)
    # Each product carries its own minimum term, so contract value is summed per line.
    contract_value_min = sum(line["monthly_min"] * line["contract_months"] for line in lines) + setup
    return {
        "lines": lines, "monthly_min": monthly_min, "monthly_max": monthly_max, "setup_total": setup,
        "first_bill_min": monthly_min + setup, "longest_commitment_months": commitment,
        "contract_value_min": contract_value_min, "install_days": install,
        "explanation": (
            f"Monthly price is the sum of each product's catalogue price times its quantity: "
            f"Rs {monthly_min:,} at the lowest catalogue rate, never more than Rs {monthly_max:,}. "
            f"One-time setup is Rs {setup:,}. Your final rate inside this range is confirmed after the site check. "
            "No discount has been applied."
        ),
    }
