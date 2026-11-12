"""Small PayPal Invoicing v2 adapter. Every URL is pinned to Sandbox."""
from __future__ import annotations

from datetime import date, timedelta
from decimal import Decimal
import time
import re

import httpx

from app.schemas import InvoiceDraft

SANDBOX_API = "https://api-m.sandbox.paypal.com"


class PayPalAPIError(RuntimeError):
    """A sanitized PayPal error safe to show to the user."""


def _safe_error_token(value: object, pattern: str, limit: int) -> str | None:
    text = str(value or "")[:limit]
    return text if text and re.fullmatch(pattern, text) else None


def _paypal_error_message(response: httpx.Response) -> str:
    parts = [f"PayPal Sandbox rejected the request (HTTP {response.status_code})"]
    try:
        data = response.json()
    except ValueError:
        data = {}
    if not isinstance(data, dict):
        data = {}

    name = _safe_error_token(data.get("name"), r"[A-Z0-9_]+", 80)
    if name:
        parts.append(f"name={name}")

    details = data.get("details")
    if isinstance(details, list):
        for item in details[:3]:
            if not isinstance(item, dict):
                continue
            issue = _safe_error_token(item.get("issue"), r"[A-Z0-9_]+", 80)
            field = _safe_error_token(item.get("field"), r"[/A-Za-z0-9_.\[\]-]+", 200)
            diagnostic = ", ".join(value for value in (f"issue={issue}" if issue else None, f"field={field}" if field else None) if value)
            if diagnostic:
                parts.append(diagnostic)

    debug_id = _safe_error_token(data.get("debug_id"), r"[A-Za-z0-9_-]+", 100)
    if debug_id:
        parts.append(f"debug_id={debug_id}")
    return "; ".join(parts)


def map_provider_status(status: str) -> str:
    normalized = status.upper()
    if normalized in {"PAID", "MARKED_AS_PAID"}:
        return "PAID"
    if normalized in {"CANCELLED", "CANCELED"}:
        return "CANCELLED"
    if normalized == "DRAFT":
        return "DRAFT"
    return "SENT"


class PayPalClient:
    def __init__(self, client_id: str, client_secret: str, *, environment: str = "sandbox", timeout: float = 15):
        if environment.lower() != "sandbox":
            raise ValueError("Only PayPal Sandbox is supported")
        if not client_id or not client_secret:
            raise ValueError("PayPal Sandbox credentials are required")
        self.client_id = client_id
        self.client_secret = client_secret
        self.http = httpx.Client(timeout=timeout)
        self._token: str | None = None
        self._token_expiry = 0.0

    def _access_token(self) -> str:
        if self._token and time.monotonic() < self._token_expiry:
            return self._token
        try:
            response = self.http.post(
                f"{SANDBOX_API}/v1/oauth2/token",
                auth=(self.client_id, self.client_secret),
                headers={"Accept": "application/json", "Accept-Language": "en_US"},
                data={"grant_type": "client_credentials"},
            )
            response.raise_for_status()
            data = response.json()
            self._token = data["access_token"]
            self._token_expiry = time.monotonic() + max(0, int(data.get("expires_in", 300)) - 30)
            return self._token
        except (httpx.HTTPError, KeyError, ValueError) as exc:
            raise RuntimeError("PayPal authentication failed") from exc

    def _request(self, method: str, path: str, *, request_id: str | None = None, json: dict | None = None) -> dict:
        headers = {"Authorization": f"Bearer {self._access_token()}", "Accept": "application/json"}
        if request_id:
            headers["PayPal-Request-Id"] = request_id
        try:
            response = self.http.request(method, f"{SANDBOX_API}{path}", headers=headers, json=json)
            response.raise_for_status()
        except httpx.HTTPStatusError as exc:
            raise PayPalAPIError(_paypal_error_message(exc.response)) from exc
        except httpx.HTTPError as exc:
            raise RuntimeError("PayPal Sandbox request failed; inspect the action before retrying") from exc
        if not response.content:
            return {}
        try:
            return response.json()
        except ValueError as exc:
            raise RuntimeError("PayPal Sandbox returned an invalid response") from exc

    @staticmethod
    def invoice_payload(draft: InvoiceDraft) -> dict:
        due = date.today() + timedelta(days=draft.due_in_days)
        payload = {
            "detail": {
                "currency_code": draft.currency,
                "invoice_date": date.today().isoformat(),
                "payment_term": {"term_type": "DUE_ON_DATE_SPECIFIED", "due_date": due.isoformat()},
            },
            "primary_recipients": [{"billing_info": {"name": {"given_name": draft.client_name}, "email_address": str(draft.client_email)}}],
            "items": [{"name": item.description, "description": item.description, "quantity": str(item.quantity), "unit_amount": {"currency_code": draft.currency, "value": f"{item.unit_price:.2f}"}} for item in draft.items],
        }
        if draft.note:
            payload["detail"]["note"] = draft.note
        return payload

    def create_and_send(self, draft: InvoiceDraft, request_id: str) -> str:
        created = self._request("POST", "/v2/invoicing/invoices", request_id=f"{request_id}-create", json=self.invoice_payload(draft))
        invoice_id = created.get("id")
        if not invoice_id:
            raise RuntimeError("PayPal Sandbox did not return an invoice ID")
        self._request(
            "POST",
            f"/v2/invoicing/invoices/{invoice_id}/send",
            request_id=f"{request_id}-send",
            json={"send_to_invoicer": True},
        )
        return invoice_id

    def get_invoice(self, invoice_id: str) -> dict:
        return self._request("GET", f"/v2/invoicing/invoices/{invoice_id}")

    def send_reminder(self, invoice_id: str, request_id: str) -> None:
        self._request("POST", f"/v2/invoicing/invoices/{invoice_id}/remind", request_id=request_id, json={"subject": "Invoice payment reminder", "note": "Please review your outstanding invoice."})

    def cancel_invoice(self, invoice_id: str, request_id: str) -> None:
        self._request("POST", f"/v2/invoicing/invoices/{invoice_id}/cancel", request_id=request_id, json={"send_to_recipient": True})

    def close(self) -> None:
        self.http.close()
