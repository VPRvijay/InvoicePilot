from __future__ import annotations

from decimal import Decimal

import pytest
from pydantic import ValidationError

from app.schemas import (
    Invoice,
    InvoiceDraft,
    InvoiceDraftItem,
    InvoiceStatus,
    PendingAction,
    PendingActionStatus,
    PendingActionType,
)


def test_invoice_draft_uses_usd_and_sums_line_items() -> None:
    draft = InvoiceDraft(
        client_name="Acme",
        client_email="billing@acme.example",
        items=[
            InvoiceDraftItem(description="Logo", quantity=1, unit_price="1200.00"),
            InvoiceDraftItem(description="Rush fee", quantity=2, unit_price="25.00"),
        ],
        due_in_days=15,
    )

    assert draft.currency == "USD"
    assert draft.total == Decimal("1250.00")


def test_invoice_draft_rejects_invalid_email_and_nonpositive_fields() -> None:
    with pytest.raises(ValidationError):
        InvoiceDraft(
            client_name="Acme",
            client_email="not-an-email",
            items=[InvoiceDraftItem(description="Logo", quantity=0, unit_price="10")],
            due_in_days=0,
        )


def test_currency_is_normalized_to_uppercase() -> None:
    draft = InvoiceDraft(
        client_name="Acme",
        client_email="billing@acme.example",
        items=[InvoiceDraftItem(description="Logo", quantity=1, unit_price="1.25")],
        currency="usd",
        due_in_days=1,
    )
    assert draft.currency == "USD"


def test_pending_action_accepts_only_known_types_and_statuses() -> None:
    action = PendingAction(
        id="action-1",
        type=PendingActionType.CREATE_AND_SEND_INVOICE,
        payload={"draft": {"client_name": "Acme"}},
    )
    assert action.status == PendingActionStatus.PENDING


def test_invoice_defaults_to_draft() -> None:
    invoice = Invoice(
        id="invoice-1",
        paypal_invoice_id=None,
        draft=InvoiceDraft(
            client_name="Acme",
            client_email="billing@acme.example",
            items=[InvoiceDraftItem(description="Logo", quantity=1, unit_price="99.99")],
            due_in_days=15,
        ),
        total=Decimal("99.99"),
        due_date="2026-11-24",
    )
    assert invoice.status == InvoiceStatus.DRAFT
