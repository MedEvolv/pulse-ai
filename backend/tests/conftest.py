"""Pytest fixtures with strict test isolation (CP-09.4).

- Defaults to the in-memory adapter so the suite is self-contained (the same
  adapter the public demo ships on). Set MONGO_URL in the environment to run the
  fabric tests against a real Mongo; a dedicated _test DB is then enforced.
- Disables model calls so no automated test can reach a provider.
- Provides a FastAPI TestClient bound to the selected adapter.
"""
import os
import sys

# Configure BEFORE importing the app. load_dotenv(override=False) will not clobber these.
os.environ["DB_NAME"] = os.environ.get("DB_NAME_TEST", "pulse_ai_test")
os.environ["MODEL_ENABLED"] = "false"          # no model calls in automated tests
# NOTE: MONGO_URL is deliberately NOT defaulted. Absent -> server uses the
# in-memory adapter (_MemDB), so tests run with no external service. To exercise
# the Mongo path, export MONGO_URL before running pytest.
os.environ.setdefault("CORS_ORIGINS", "*")

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pytest  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402

# Hard guard: refuse to run against the demo database.
if os.environ["DB_NAME"] in ("pulse_ai", "pulse"):
    raise RuntimeError("Refusing to run tests against the demo database. Set DB_NAME_TEST.")

import server  # noqa: E402


@pytest.fixture(scope="session")
def app_client():
    with TestClient(server.app) as client:
        yield client


@pytest.fixture()
def session_header():
    import uuid
    return {"X-Demo-Session-ID": f"test-{uuid.uuid4().hex[:12]}"}


@pytest.fixture(autouse=True, scope="session")
def _cleanup_test_db():
    yield
    # In-memory adapter: nothing external to drop.
    mongo_url = os.environ.get("MONGO_URL")
    if not mongo_url:
        return
    # Drop the isolated test DB at the end of the session.
    from pymongo import MongoClient
    name = os.environ["DB_NAME"]
    if name.endswith("_test"):
        MongoClient(mongo_url).drop_database(name)
