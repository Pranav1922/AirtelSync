"""Loads the supplied synthetic CSVs once and exposes typed lookups.

The CSV files are the single source of truth: no record is copied into code.
"""
from __future__ import annotations

from dataclasses import dataclass
from functools import lru_cache

import pandas as pd

from .config import DATA_DIR

SEGMENT_CODES = {
    "Micro retail & services": "micro",
    "Professional offices": "prof",
    "Small multi-site businesses": "multi",
    "Small manufacturers": "mfg",
}
SEGMENT_NAMES = {v: k for k, v in SEGMENT_CODES.items()}


@dataclass(frozen=True)
class Product:
    id: str
    category: str
    name: str
    description: str
    unit: str
    price_min: int
    price_max: int
    setup_fee: int
    min_contract_months: int
    city_tiers: frozenset[int]
    min_employees: int
    min_sites: int
    requires_gstin: bool
    requires_one_of: frozenset[str]
    install_days: int
    target_segments: frozenset[str]

    def public(self) -> dict:
        return {
            "id": self.id, "category": self.category, "name": self.name,
            "description": self.description, "unit": self.unit,
            "price_min": self.price_min, "price_max": self.price_max,
            "setup_fee": self.setup_fee, "min_contract_months": self.min_contract_months,
            "city_tiers": sorted(self.city_tiers), "min_employees": self.min_employees,
            "min_sites": self.min_sites, "requires_gstin": self.requires_gstin,
            "requires_one_of": sorted(self.requires_one_of), "install_days": self.install_days,
            "target_segments": sorted(self.target_segments),
        }


def _split(v, sep):
    return frozenset(x.strip() for x in str(v).split(sep) if x.strip()) if isinstance(v, str) else frozenset()


@lru_cache(maxsize=1)
def catalogue() -> dict[str, Product]:
    df = pd.read_csv(DATA_DIR / "product_catalogue.csv")
    out = {}
    for r in df.itertuples(index=False):
        out[r.product_id] = Product(
            id=r.product_id, category=r.category, name=r.product_name, description=r.description,
            unit=r.unit, price_min=int(r.price_min_inr_per_month), price_max=int(r.price_max_inr_per_month),
            setup_fee=int(r.one_time_setup_inr), min_contract_months=int(r.min_contract_months),
            city_tiers=frozenset(int(x) for x in _split(str(r.available_city_tiers), ";")),
            min_employees=int(r.min_employees), min_sites=int(r.min_sites),
            requires_gstin=r.requires_gstin == "Y", requires_one_of=_split(r.requires_one_of, "|"),
            install_days=int(r.typical_install_days), target_segments=_split(r.target_segments, ";"),
        )
    return out


@lru_cache(maxsize=1)
def leads() -> pd.DataFrame:
    df = pd.read_csv(DATA_DIR / "smb_leads.csv", dtype={"gstin": str, "udyam_number": str})
    df["segment_code"] = df["segment"].map(SEGMENT_CODES)
    for col in ["contacted", "needs_assessed", "quote_accepted", "kyc_complete", "activated"]:
        df[f"reached_{col}"] = df[f"{col}_date"].notna()
    return df


@lru_cache(maxsize=1)
def gstin_registry() -> dict[str, dict]:
    df = pd.read_csv(DATA_DIR / "mock_gstin_registry.csv", dtype=str)
    return {r["gstin"]: r for r in df.to_dict("records")}


@lru_cache(maxsize=1)
def udyam_registry() -> dict[str, dict]:
    df = pd.read_csv(DATA_DIR / "mock_udyam_registry.csv", dtype=str)
    return {r["udyam_number"]: r for r in df.to_dict("records")}


@lru_cache(maxsize=1)
def city_tiers() -> dict[str, dict]:
    """City -> tier/state, derived from the leads file (the only source of city tiers)."""
    df = leads()[["city", "city_tier", "state"]].drop_duplicates("city")
    return {r.city: {"tier": int(r.city_tier), "state": r.state} for r in df.itertuples()}


@lru_cache(maxsize=1)
def business_types() -> dict[str, str]:
    """Business type -> most common segment code, derived from the leads file."""
    df = leads().groupby("business_type")["segment_code"].agg(lambda s: s.mode().iloc[0])
    return df.to_dict()


def lead(lead_id: str) -> dict | None:
    df = leads()
    hit = df[df.lead_id == lead_id]
    if hit.empty:
        return None
    return {k: (None if pd.isna(v) else v) for k, v in hit.iloc[0].to_dict().items()}
