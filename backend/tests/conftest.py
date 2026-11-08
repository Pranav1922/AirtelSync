import os
import sys
import tempfile
from pathlib import Path

_tmp = tempfile.mkdtemp(prefix="sync-test-")
os.environ["SYNC_DB_PATH"] = str(Path(_tmp) / "test.db")
os.environ["SYNC_UPLOAD_DIR"] = str(Path(_tmp) / "uploads")
os.environ.pop("ANTHROPIC_API_KEY", None)  # tests must prove the LLM is optional
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import pytest  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402

from app.main import app  # noqa: E402

SPECIMENS = Path(__file__).resolve().parents[2] / "YTL_TrackA_Udyam_Digital_Data" / "kyc_documents"


@pytest.fixture(scope="session")
def client():
    with TestClient(app) as c:
        yield c


@pytest.fixture
def console():
    return {"X-Console-Key": "demo-console"}
