import json

import httpx
import pytest
import respx

from app.paypal_client import PayPalAPIError, PayPalClient, map_provider_status
from app.schemas import InvoiceDraft


@pytest.fixture
def paypal():
    return PayPalClient("client", "secret")


@respx.mock
def test_create_and_send_uses_sandbox_and_stable_request_ids(paypal):
    respx.post("https://api-m.sandbox.paypal.com/v1/oauth2/token").mock(
        return_value=httpx.Response(200, json={"access_token": "token", "expires_in": 3600})
    )
    created = respx.post("https://api-m.sandbox.paypal.com/v2/invoicing/invoices").mock(
        return_value=httpx.Response(201, json={"id": "INV-1"})
    )
    sent = respx.post("https://api-m.sandbox.paypal.com/v2/invoicing/invoices/INV-1/send").mock(
        return_value=httpx.Response(204)
    )
    draft = InvoiceDraft(client_name="Acme", client_email="billing@acme.com", items=[{"description": "Design", "quantity": 2, "unit_price": "10.00"}], due_in_days=14)

    assert paypal.create_and_send(draft, "action-123") == "INV-1"
    assert created.calls[0].request.headers["PayPal-Request-Id"] == "action-123-create"
    assert sent.calls[0].request.headers["PayPal-Request-Id"] == "action-123-send"
    assert json.loads(sent.calls[0].request.content) == {"send_to_invoicer": True}
    assert created.calls[0].request.url.host == "api-m.sandbox.paypal.com"


@respx.mock
def test_provider_errors_are_sanitized(paypal):
    respx.post("https://api-m.sandbox.paypal.com/v1/oauth2/token").mock(
        return_value=httpx.Response(401, json={"error": "invalid_client", "error_description": "client secret leaked"})
    )
    with pytest.raises(RuntimeError, match="PayPal authentication failed") as err:
        paypal.get_invoice("INV-1")
    assert "leaked" not in str(err.value)


@respx.mock
def test_provider_http_errors_include_safe_paypal_diagnostics(paypal):
    respx.post("https://api-m.sandbox.paypal.com/v1/oauth2/token").mock(
        return_value=httpx.Response(200, json={"access_token": "token", "expires_in": 3600})
    )
    respx.get("https://api-m.sandbox.paypal.com/v2/invoicing/invoices/INV-1").mock(
        return_value=httpx.Response(
            422,
            headers={"Content-Type": "application/json"},
            json={
                "name": "UNPROCESSABLE_ENTITY",
                "message": "Request is invalid",
                "debug_id": "sandbox-debug-123",
                "details": [{"issue": "INVALID_FIELD", "field": "/items/0/name", "description": "contains private data"}],
            },
        )
    )

    with pytest.raises(PayPalAPIError) as err:
        paypal.get_invoice("INV-1")

    message = str(err.value)
    assert "422" in message
    assert "INVALID_FIELD" in message
    assert "/items/0/name" in message
    assert "sandbox-debug-123" in message
    assert "private data" not in message


def test_production_environment_is_rejected():
    with pytest.raises(ValueError, match="Sandbox"):
        PayPalClient("client", "secret", environment="production")


@pytest.mark.parametrize(
    ("provider_status", "expected"),
    [("PAID", "PAID"), ("MARKED_AS_PAID", "PAID"), ("CANCELLED", "CANCELLED"), ("DRAFT", "DRAFT"), ("PARTIALLY_PAID", "SENT"), ("UNKNOWN", "SENT")],
)
def test_provider_status_mapping_never_promotes_unknown_status(provider_status, expected):
    assert map_provider_status(provider_status) == expected
