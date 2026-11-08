"""Identifier validation and mock registry lookups.

Every lookup here is against the supplied *mock* CSV registries. No real GST,
Udyam, DigiLocker or e-sign service is called anywhere in this codebase.
"""
from __future__ import annotations

import re

from ..data import gstin_registry, udyam_registry

_CHARSET = "0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZ"
# 2 digit state | 5 letter PAN prefix | 4 digit | 1 letter | entity no. | 'Z' | checksum
GSTIN_RE = re.compile(r"^[0-9]{2}[A-Z]{5}[0-9]{4}[A-Z][1-9A-Z]Z[0-9A-Z]$")
UDYAM_RE = re.compile(r"^UDYAM-([A-Z]{2})-(\d{2})-(\d{7})$")
# 4th char of the embedded PAN (index 5 of the GSTIN) is the holder type.
# Real types are P,C,H,F,A,T,B,L,J,G. The dataset uses 'X' on purpose (README).
VALID_PAN_TYPES = set("PCHFATBLJG") | {"X"}

GST_STATE_CODES = {
    "03": "Punjab", "07": "Delhi", "08": "Rajasthan", "09": "Uttar Pradesh", "10": "Bihar",
    "19": "West Bengal", "23": "Madhya Pradesh", "24": "Gujarat", "27": "Maharashtra",
    "29": "Karnataka", "32": "Kerala", "33": "Tamil Nadu", "36": "Telangana", "37": "Andhra Pradesh",
}
UDYAM_STATE_CODES = {
    "PB": "Punjab", "DL": "Delhi", "RJ": "Rajasthan", "UP": "Uttar Pradesh", "BR": "Bihar",
    "WB": "West Bengal", "MP": "Madhya Pradesh", "GJ": "Gujarat", "MH": "Maharashtra",
    "KR": "Karnataka", "KL": "Kerala", "TN": "Tamil Nadu", "TS": "Telangana", "AP": "Andhra Pradesh",
}

# OCR confusions, applied only where the GSTIN grammar says a digit or a letter belongs.
_TO_DIGIT = str.maketrans({"O": "0", "D": "0", "Q": "0", "I": "1", "L": "1", "Z": "2", "S": "5", "B": "8", "G": "6"})
_TO_ALPHA = str.maketrans({"0": "O", "1": "I", "2": "Z", "5": "S", "8": "B", "6": "G"})
_DIGIT_POS = {0, 1, 7, 8, 9, 10}
_ALPHA_POS = {2, 3, 4, 5, 6, 11}


def gstin_checksum(first14: str) -> str:
    total = 0
    for i, ch in enumerate(first14):
        v = _CHARSET.index(ch) * (2 if i % 2 else 1)
        total += v // 36 + v % 36
    return _CHARSET[(36 - total % 36) % 36]


def normalise_gstin(raw: str) -> str:
    """Upper-case, drop spaces, and repair OCR digit/letter swaps by position."""
    s = re.sub(r"[^0-9A-Za-z]", "", raw or "").upper()
    if len(s) != 15:
        return s
    chars = list(s)
    for i in _DIGIT_POS:
        chars[i] = chars[i].translate(_TO_DIGIT)
    for i in _ALPHA_POS:
        chars[i] = chars[i].translate(_TO_ALPHA)
    if chars[13] == "2":
        chars[13] = "Z"
    return "".join(chars)


def validate_gstin_format(gstin: str) -> dict:
    """Structural checks only. Returns {valid, reasons[]}."""
    reasons = []
    if len(gstin) != 15:
        return {"valid": False, "reasons": [f"GSTIN must be 15 characters, found {len(gstin)}."]}
    if not GSTIN_RE.match(gstin):
        reasons.append("Characters do not follow the GSTIN pattern (2 digits, PAN, entity, Z, checksum).")
    if gstin[:2] not in GST_STATE_CODES:
        reasons.append(f"State code {gstin[:2]} is not one of the dataset states.")
    if gstin[5] not in VALID_PAN_TYPES:
        reasons.append(f"PAN holder type '{gstin[5]}' is not recognised.")
    if not reasons and gstin_checksum(gstin[:14]) != gstin[14]:
        reasons.append(f"Checksum digit is '{gstin[14]}' but should be '{gstin_checksum(gstin[:14])}' - "
                       "the number is mistyped or altered.")
    return {"valid": not reasons, "reasons": reasons}


def lookup_gstin(gstin: str) -> dict:
    """Format check + mock registry lookup. status: active|cancelled|suspended|not_found|invalid_format."""
    g = normalise_gstin(gstin)
    fmt = validate_gstin_format(g)
    if not fmt["valid"]:
        return {"gstin": g, "status": "invalid_format", "reasons": fmt["reasons"], "record": None,
                "source": "format check"}
    rec = gstin_registry().get(g)
    if rec is None:
        return {"gstin": g, "status": "not_found", "record": None, "source": "mock GSTIN registry",
                "reasons": ["Valid format but no record in the mock GSTIN registry."]}
    status = rec["status"].lower()
    reasons = [] if status == "active" else [f"Registry status is {rec['status']}. Products that need a GSTIN cannot be sold."]
    return {"gstin": g, "status": status, "record": rec, "source": "mock GSTIN registry", "reasons": reasons}


# Glyph pairs Tesseract confuses in the certificate font. Deliberately narrow so a real
# alteration (e.g. 5 -> 8) is never "repaired".
OCR_CONFUSABLE = {"I": "TJ1L", "T": "I", "J": "I", "1": "I", "L": "I", "O": "0DQ", "0": "OD", "D": "0O",
                  "Q": "O0", "S": "5", "5": "S", "B": "8", "8": "B", "Z": "2", "2": "Z", "G": "6", "6": "G"}


def checksum_repair(gstin: str) -> dict | None:
    """If a GSTIN fails its checksum, try single OCR-confusable substitutions. Accept only when exactly
    one candidate is both checksum-valid and present in the mock registry."""
    if len(gstin) != 15:
        return None
    hits = []
    for i, ch in enumerate(gstin):
        for alt in OCR_CONFUSABLE.get(ch, ""):
            cand = gstin[:i] + alt + gstin[i + 1:]
            if validate_gstin_format(cand)["valid"] and cand in gstin_registry():
                hits.append({"gstin": cand, "position": i + 1, "read": ch, "corrected": alt})
    return hits[0] if len(hits) == 1 else None


def nearest_gstin(gstin: str) -> str | None:
    """Registry GSTIN that differs by exactly one character (likely typo or alteration)."""
    if len(gstin) != 15:
        return None
    canon = gstin.replace("O", "0")
    for g in gstin_registry():
        if sum(a != b for a, b in zip(g.replace("O", "0"), canon)) == 1:
            return g
    return None


def normalise_udyam(raw: str) -> str:
    s = re.sub(r"\s+", "", (raw or "").upper())
    m = re.match(r"^UDYAM[-–]?([A-Z]{2})[-–]?([0-9O]{2})[-–]?([0-9O]{7})$", s)
    if not m:
        return s
    return f"UDYAM-{m.group(1)}-{m.group(2).replace('O', '0')}-{m.group(3).replace('O', '0')}"


def lookup_udyam(udyam: str) -> dict:
    u = normalise_udyam(udyam)
    m = UDYAM_RE.match(u)
    if not m:
        return {"udyam_number": u, "status": "invalid_format", "record": None, "source": "format check",
                "reasons": ["Udyam number must look like UDYAM-XX-00-0000000."]}
    reasons = []
    if m.group(1) not in UDYAM_STATE_CODES:
        reasons.append(f"State code {m.group(1)} is not one of the dataset states.")
    # README: district code 00 is intentionally fictional in this dataset; accept it.
    rec = udyam_registry().get(u)
    if rec is None:
        return {"udyam_number": u, "status": "not_found", "record": None, "source": "mock Udyam registry",
                "reasons": reasons + ["No record in the mock Udyam registry."]}
    return {"udyam_number": u, "status": "found", "record": rec, "source": "mock Udyam registry", "reasons": reasons}


def mask_id(value: str | None, keep: int = 4) -> str:
    """Mask identifiers for UI and logs: 27XUIXG0767D1ZP -> 27•••••••••D1ZP."""
    if not value:
        return ""
    v = str(value)
    if len(v) <= keep + 2:
        return "•" * len(v)
    return v[:2] + "•" * (len(v) - keep - 2) + v[-keep:]
