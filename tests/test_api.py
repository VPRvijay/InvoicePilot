from datetime import date, timedelta
import os
import subprocess
import sys
from pathlib import Path

from fastapi.testclient import TestClient

from app import db
from app import main
from app.main import app
from app.paypal_client import PayPalAPIError


def test_main_loads_dotenv_before_database_path_is_imported():
    project_root = Path(__file__).resolve().parents[1]
    configured_path = os.environ.get("DATABASE_PATH")
    if configured_path is None:
        from dotenv import dotenv_values
        configured_path = dotenv_values(project_root / ".env").get("DATABASE_PATH", "data/invoicepilot.db")
    child_env = os.environ.copy()
    child_env.pop("DATABASE_PATH", None)

    result = subprocess.run(
        [sys.executable, "-c", "from app import main, db; print(db.DATABASE_PATH)"],
        cwd=project_root,
        env=child_env,
        capture_output=True,
        check=True,
        text=True,
    )

    assert Path(result.stdout.strip()) == Path(configured_path)


def client_for(tmp_path, monkeypatch):
    monkeypatch.setattr(db, "DATABASE_PATH", str(tmp_path / "test.db"), raising=False)
    monkeypatch.setenv("DEMO_MODE", "true")
    return TestClient(app)


def test_health_and_seeded_demo_invoices(tmp_path, monkeypatch):
    client = client_for(tmp_path, monkeypatch)
    assert client.get("/health").json()["mode"] == "demo"
    invoices = client.get("/invoices").json()["invoices"]
    assert len(invoices) >= 3


def test_chat_creates_pending_action_and_confirm_creates_demo_invoice(tmp_path, monkeypatch):
    client = client_for(tmp_path, monkeypatch)
    response = client.post("/chat", json={"session_id": "s1", "message": "Invoice Acme, billing@acme.com, $125 for design due in 15 days"})
    action = response.json()["pending_action"]
    assert action["status"] == "PENDING"
    assert client.get("/invoices").json()["invoices"]
    confirmed = client.post(f"/actions/{action['id']}/confirm")
    assert confirmed.status_code == 200
    assert confirmed.json()["invoice"]["status"] == "SENT"
    assert client.post(f"/actions/{action['id']}/confirm").status_code == 409


def test_cancel_pending_action_does_not_create_invoice(tmp_path, monkeypatch):
    client = client_for(tmp_path, monkeypatch)
    response = client.post("/chat", json={"session_id": "s1", "message": "Invoice Acme billing@acme.com for $20 for consult"})
    action_id = response.json()["pending_action"]["id"]
    before = len(client.get("/invoices").json()["invoices"])
    assert client.post(f"/actions/{action_id}/cancel").json()["action"]["status"] == "CANCELLED"
    assert len(client.get("/invoices").json()["invoices"]) == before


def test_missing_fields_are_requested_without_action(tmp_path, monkeypatch):
    client = client_for(tmp_path, monkeypatch)
    response = client.post("/chat", json={"session_id": "s1", "message": "Create an invoice"}).json()
    assert response["pending_action"] is None
    assert "email" in response["reply"].lower()


def test_claude_agent_output_becomes_pending_action_only_after_validation(tmp_path, monkeypatch):
    monkeypatch.setattr(db, "DATABASE_PATH", str(tmp_path / "claude.db"), raising=False)
    monkeypatch.setenv("DEMO_MODE", "true")
    monkeypatch.setenv("AGENT_MODE", "claude")
    monkeypatch.setenv("ANTHROPIC_API_KEY", "test-key")

    class FakeAgent:
        def respond(self, message):
            from app.schemas import InvoiceDraft, InvoiceDraftItem

            return "Review the prepared draft.", InvoiceDraft(
                client_name="Acme",
                client_email="billing@example.com",
                items=[InvoiceDraftItem(description="Design", quantity=1, unit_price="20.00")],
                due_in_days=30,
            )

    monkeypatch.setattr(main, "ClaudeAgent", lambda **kwargs: FakeAgent())
    client = TestClient(app)

    result = client.post("/chat", json={"session_id": "s-ai", "message": "Invoice Acme"}).json()

    assert result["reply"] == "Review the prepared draft."
    assert result["pending_action"]["status"] == "PENDING"
    assert result["pending_action"]["payload"]["draft"]["client_email"] == "billing@example.com"

from datetime import date, timedelta

from fastapi.testclient import TestClient

from app import db
from app.main import app


def test_dashboard_insights_and_overdue_refresh(tmp_path, monkeypatch):
    monkeypatch.setattr(db, "DATABASE_PATH", str(tmp_path / "dashboard.db"), raising=False)
    monkeypatch.setenv("DEMO_MODE", "true")
    client = TestClient(app)
    invoices = client.get("/invoices").json()["invoices"]
    overdue = next(row for row in invoices if row["status"] == "OVERDUE")
    result = client.get("/insights").json()
    assert float(result["outstanding"]) >= float(result["overdue"]) > 0
    assert client.post(f"/invoices/{overdue['id']}/refresh").json()["status"] == "OVERDUE"


def test_unknown_invoice_returns_404(tmp_path, monkeypatch):
    monkeypatch.setattr(db, "DATABASE_PATH", str(tmp_path / "missing.db"), raising=False)
    monkeypatch.setenv("DEMO_MODE", "true")
    client = TestClient(app)
    assert client.get("/invoices/not-here").status_code == 404


def test_read_only_chat_answers_without_pending_action(tmp_path, monkeypatch):
    monkeypatch.setattr(db, "DATABASE_PATH", str(tmp_path / "read-only.db"), raising=False)
    monkeypatch.setenv("DEMO_MODE", "true")
    client = TestClient(app)
    result = client.post("/chat", json={"session_id": "s1", "message": "What is outstanding?"}).json()
    assert "outstanding" in result["reply"].lower()
    assert result["pending_action"] is None


def test_sandbox_provider_is_called_only_after_explicit_confirmation(tmp_path, monkeypatch):
    monkeypatch.setattr(db, "DATABASE_PATH", str(tmp_path / "sandbox.db"), raising=False)
    monkeypatch.setenv("DEMO_MODE", "false")
    monkeypatch.setenv("PAYPAL_ENVIRONMENT", "sandbox")
    monkeypatch.setenv("PAYPAL_CLIENT_ID", "test-client")
    monkeypatch.setenv("PAYPAL_CLIENT_SECRET", "test-secret")

    class FakeProvider:
        def __init__(self):
            self.calls = []

        def create_and_send(self, draft, action_id):
            self.calls.append((draft, action_id))
            return "SANDBOX-INV-1"

        def close(self):
            pass

    provider = FakeProvider()
    monkeypatch.setattr(main, "_provider", lambda: provider)
    client = TestClient(app)
    response = client.post("/chat", json={"session_id": "sandbox", "message": "Invoice Acme billing@acme.com for $20 for consult"})
    action = response.json()["pending_action"]
    assert provider.calls == []

    confirmed = client.post(f"/actions/{action['id']}/confirm")
    assert confirmed.status_code == 200
    assert confirmed.json()["invoice"]["paypal_invoice_id"] == "SANDBOX-INV-1"
    assert len(provider.calls) == 1


def test_sandbox_provider_diagnostics_reach_confirmation_response(tmp_path, monkeypatch):
    monkeypatch.setattr(db, "DATABASE_PATH", str(tmp_path / "sandbox-error.db"), raising=False)
    monkeypatch.setenv("DEMO_MODE", "false")
    monkeypatch.setenv("PAYPAL_ENVIRONMENT", "sandbox")
    monkeypatch.setenv("PAYPAL_CLIENT_ID", "test-client")
    monkeypatch.setenv("PAYPAL_CLIENT_SECRET", "test-secret")

    class FailingProvider:
        def create_and_send(self, draft, action_id):
            raise PayPalAPIError("PayPal Sandbox rejected request (HTTP 422; issue=INVALID_FIELD; field=/items/0/name; debug_id=sandbox-debug-123)")

        def close(self):
            pass

    monkeypatch.setattr(main, "_provider", lambda: FailingProvider())
    client = TestClient(app)
    drafted = client.post("/chat", json={"session_id": "sandbox", "message": "Invoice Acme billing@acme.com for $20 for consult"}).json()
    action_id = drafted["pending_action"]["id"]

    response = client.post(f"/actions/{action_id}/confirm")

    assert response.status_code == 422
    assert "INVALID_FIELD" in response.json()["detail"]
    assert "/items/0/name" in response.json()["detail"]
    assert db.get_action(action_id).status.value == "FAILED"


def test_sandbox_mode_does_not_seed_fictional_demo_invoices(tmp_path, monkeypatch):
    monkeypatch.setattr(db, "DATABASE_PATH", str(tmp_path / "sandbox-empty.db"), raising=False)
    monkeypatch.setenv("DEMO_MODE", "false")
    monkeypatch.setenv("PAYPAL_ENVIRONMENT", "sandbox")
    monkeypatch.setenv("PAYPAL_CLIENT_ID", "test-client")
    monkeypatch.setenv("PAYPAL_CLIENT_SECRET", "test-secret")
    client = TestClient(app)

    assert client.get("/invoices").json()["invoices"] == []
