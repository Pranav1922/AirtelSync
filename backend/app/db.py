"""SQLite persistence (stdlib sqlite3). One file, created on first start."""
from __future__ import annotations

import json
import sqlite3
import threading
import uuid
from datetime import datetime, timezone

from .config import DB_PATH

SCHEMA = """
CREATE TABLE IF NOT EXISTS customers (
  id TEXT PRIMARY KEY, business_name TEXT, segment TEXT, city TEXT, language TEXT,
  contact_name TEXT, contact_role TEXT, source TEXT, created_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS advisor_sessions (
  id TEXT PRIMARY KEY, customer_id TEXT REFERENCES customers(id), language TEXT NOT NULL DEFAULT 'en',
  profile_json TEXT NOT NULL DEFAULT '{}', messages_json TEXT NOT NULL DEFAULT '[]',
  status TEXT NOT NULL DEFAULT 'open', scenario TEXT, created_at TEXT NOT NULL, updated_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS products (
  id TEXT PRIMARY KEY, name TEXT NOT NULL, category TEXT NOT NULL, unit TEXT NOT NULL,
  price_min INTEGER NOT NULL, price_max INTEGER NOT NULL, setup_fee INTEGER NOT NULL,
  min_contract_months INTEGER NOT NULL, install_days INTEGER NOT NULL
);
CREATE TABLE IF NOT EXISTS quotes (
  id TEXT PRIMARY KEY, session_id TEXT REFERENCES advisor_sessions(id), customer_id TEXT REFERENCES customers(id),
  level TEXT, profile_json TEXT NOT NULL, monthly_min INTEGER NOT NULL, monthly_max INTEGER NOT NULL,
  setup_total INTEGER NOT NULL, commitment_months INTEGER NOT NULL, install_days INTEGER NOT NULL,
  status TEXT NOT NULL DEFAULT 'draft', created_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS quote_items (
  quote_id TEXT NOT NULL REFERENCES quotes(id) ON DELETE CASCADE, product_id TEXT NOT NULL REFERENCES products(id),
  quantity INTEGER NOT NULL CHECK (quantity BETWEEN 1 AND 500), unit_price_min INTEGER NOT NULL,
  unit_price_max INTEGER NOT NULL, setup_fee INTEGER NOT NULL, contract_months INTEGER NOT NULL,
  install_days INTEGER NOT NULL, PRIMARY KEY (quote_id, product_id)
);
CREATE TABLE IF NOT EXISTS consent_records (
  id TEXT PRIMARY KEY, customer_id TEXT REFERENCES customers(id), order_id TEXT, purpose TEXT NOT NULL,
  granted INTEGER NOT NULL, notice_version TEXT NOT NULL, language TEXT, granted_at TEXT NOT NULL, withdrawn_at TEXT
);
CREATE TABLE IF NOT EXISTS kyc_cases (
  id TEXT PRIMARY KEY, order_id TEXT, customer_id TEXT REFERENCES customers(id), status TEXT NOT NULL DEFAULT 'collecting',
  decision TEXT, decision_reason TEXT, reviewer TEXT, summary_json TEXT, created_at TEXT NOT NULL, updated_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS kyc_documents (
  id TEXT PRIMARY KEY, case_id TEXT NOT NULL REFERENCES kyc_cases(id) ON DELETE CASCADE, declared_type TEXT NOT NULL,
  detected_type TEXT, stored_path TEXT, sha256 TEXT, size_bytes INTEGER, ocr_confidence REAL,
  fields_json TEXT, quality_json TEXT, created_at TEXT NOT NULL, purge_after TEXT, purged_at TEXT
);
CREATE TABLE IF NOT EXISTS verification_results (
  id INTEGER PRIMARY KEY AUTOINCREMENT, case_id TEXT NOT NULL REFERENCES kyc_cases(id) ON DELETE CASCADE,
  code TEXT NOT NULL, label TEXT NOT NULL, status TEXT NOT NULL, detail TEXT, source TEXT, created_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS orders (
  id TEXT PRIMARY KEY, order_no TEXT UNIQUE NOT NULL, quote_id TEXT NOT NULL REFERENCES quotes(id),
  customer_id TEXT REFERENCES customers(id), kyc_case_id TEXT, stage TEXT NOT NULL, payment_status TEXT NOT NULL,
  expected_activation TEXT, delay_reason TEXT, partner_code TEXT, created_at TEXT NOT NULL, updated_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS order_events (
  id INTEGER PRIMARY KEY AUTOINCREMENT, order_id TEXT NOT NULL REFERENCES orders(id) ON DELETE CASCADE,
  stage TEXT NOT NULL, note TEXT, actor TEXT NOT NULL DEFAULT 'system', at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS handoff_requests (
  id TEXT PRIMARY KEY, customer_id TEXT, session_id TEXT, order_id TEXT, reason TEXT NOT NULL,
  channel TEXT NOT NULL DEFAULT 'callback', language TEXT, context_json TEXT, status TEXT NOT NULL DEFAULT 'open',
  assigned_to TEXT, created_at TEXT NOT NULL, updated_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS audit_log (
  id INTEGER PRIMARY KEY AUTOINCREMENT, actor TEXT NOT NULL, action TEXT NOT NULL, entity TEXT, entity_id TEXT,
  detail TEXT, at TEXT NOT NULL
);
"""

_lock = threading.Lock()  # ponytail: one process-wide lock; fine for a single-node demo, use Postgres for concurrency
_conn: sqlite3.Connection | None = None


def now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def new_id(prefix: str) -> str:
    return f"{prefix}_{uuid.uuid4().hex[:12]}"


def conn() -> sqlite3.Connection:
    global _conn
    if _conn is None:
        DB_PATH.parent.mkdir(parents=True, exist_ok=True)
        _conn = sqlite3.connect(DB_PATH, check_same_thread=False)
        _conn.row_factory = sqlite3.Row
        _conn.execute("PRAGMA foreign_keys = ON")
        _conn.executescript(SCHEMA)
        _seed_products(_conn)
    return _conn


def _seed_products(c: sqlite3.Connection):
    from .data import catalogue
    c.executemany(
        "INSERT OR REPLACE INTO products VALUES (?,?,?,?,?,?,?,?,?)",
        [(p.id, p.name, p.category, p.unit, p.price_min, p.price_max, p.setup_fee, p.min_contract_months, p.install_days)
         for p in catalogue().values()],
    )
    c.commit()


def execute(sql: str, params=()) -> sqlite3.Cursor:
    with _lock:
        cur = conn().execute(sql, params)
        conn().commit()
        return cur


def many(sql: str, rows) -> None:
    with _lock:
        conn().executemany(sql, rows)
        conn().commit()


def query(sql: str, params=()) -> list[dict]:
    with _lock:
        return [dict(r) for r in conn().execute(sql, params).fetchall()]


def one(sql: str, params=()) -> dict | None:
    rows = query(sql, params)
    return rows[0] if rows else None


def insert(table: str, row: dict) -> None:
    cols = ",".join(row)
    execute(f"INSERT INTO {table} ({cols}) VALUES ({','.join('?' * len(row))})", tuple(row.values()))


def update(table: str, key: str, row: dict) -> None:
    sets = ",".join(f"{k}=?" for k in row)
    execute(f"UPDATE {table} SET {sets} WHERE id=?", (*row.values(), key))


def audit(actor: str, action: str, entity: str = "", entity_id: str = "", detail: str = "") -> None:
    insert("audit_log", {"actor": actor, "action": action, "entity": entity, "entity_id": entity_id,
                         "detail": detail, "at": now()})


def jdump(v) -> str:
    return json.dumps(v, ensure_ascii=False, default=str)


def jload(v, default=None):
    return json.loads(v) if v else default


def reset() -> None:
    """Demo reset: wipe transactional tables, keep the catalogue."""
    with _lock:
        for t in ["order_events", "orders", "verification_results", "kyc_documents", "kyc_cases", "consent_records",
                  "quote_items", "quotes", "handoff_requests", "advisor_sessions", "customers", "audit_log"]:
            conn().execute(f"DELETE FROM {t}")
        conn().commit()
