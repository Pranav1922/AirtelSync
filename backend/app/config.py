"""Runtime configuration. Everything comes from environment variables with safe local defaults."""
import os
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
DATA_DIR = Path(os.getenv("SYNC_DATA_DIR", ROOT / "YTL_TrackA_Udyam_Digital_Data"))
KYC_SPECIMEN_DIR = DATA_DIR / "kyc_documents"
DB_PATH = Path(os.getenv("SYNC_DB_PATH", ROOT / "backend" / "var" / "sync.db"))
UPLOAD_DIR = Path(os.getenv("SYNC_UPLOAD_DIR", ROOT / "backend" / "var" / "uploads"))

# README: use 2026-07-15 as "today" for every date-based check.
REFERENCE_DATE = date.fromisoformat(os.getenv("SYNC_REFERENCE_DATE", "2026-07-15"))
ADDRESS_PROOF_MAX_AGE_DAYS = 90

# Optional LLM. The product works fully without it.
ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY", "")
LLM_MODEL = os.getenv("SYNC_LLM_MODEL", "claude-haiku-5-5")

MAX_UPLOAD_BYTES = 8 * 1024 * 1024
ALLOWED_UPLOAD_TYPES = {"image/png": b"\x89PNG", "image/jpeg": b"\xff\xd8\xff"}
DOCUMENT_RETENTION_DAYS = 30  # prototype policy, see docs/PRIVACY_AND_SECURITY.md
CORS_ORIGINS = os.getenv("SYNC_CORS_ORIGINS", "http://localhost:5173,http://127.0.0.1:5173").split(",")
