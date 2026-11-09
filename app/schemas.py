from __future__ import annotations

from datetime import UTC, date, datetime
from decimal import Decimal
from enum import StrEnum
from typing import Any
import re

from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator


class ContractModel(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)


class InvoiceStatus(StrEnum):
    DRAFT = "DRAFT"
    SENT = "SENT"
    PAID = "PAID"
    OVERDUE = "OVERDUE"
    CANCELLED = "CANCELLED"


class PendingActionType(StrEnum):
    CREATE_AND_SEND_INVOICE = "create_and_send_invoice"
    CANCEL_INVOICE = "cancel_invoice"
    SEND_REMINDER = "send_reminder"


class PendingActionStatus(StrEnum):
    PENDING = "PENDING"
    EXECUTING = "EXECUTING"
    CONFIRMED = "CONFIRMED"
    CANCELLED = "CANCELLED"
    FAILED = "FAILED"


class InvoiceDraftItem(ContractModel):
    description: str = Field(min_length=1, max_length=200)
    quantity: int = Field(ge=1, le=10000)
    unit_price: Decimal = Field(ge=0, max_digits=12, decimal_places=2)


class InvoiceDraft(ContractModel):
    client_name: str = Field(min_length=1, max_length=120)
    client_email: EmailStr
    items: list[InvoiceDraftItem] = Field(min_length=1, max_length=50)
    currency: str = "USD"
    due_in_days: int = Field(ge=1, le=365)
    note: str | None = Field(default=None, max_length=1000)

    @field_validator("currency", mode="before")
    @classmethod
    def normalize_currency(cls, value: Any) -> str:
        currency = str(value or "USD").strip().upper()
        if not re.fullmatch(r"[A-Z]{3}", currency):
            raise ValueError("currency must be a three-letter ISO code")
        return currency

    @property
    def total(self) -> Decimal:
        return sum(
            (item.unit_price * item.quantity for item in self.items),
            start=Decimal("0.00"),
        )


class Invoice(ContractModel):
    id: str
    paypal_invoice_id: str | None = None
    draft: InvoiceDraft
    status: InvoiceStatus = InvoiceStatus.DRAFT
    total: Decimal = Field(ge=0, max_digits=14, decimal_places=2)
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    due_date: date
    paid_at: datetime | None = None
    provider_status: str | None = None


class PendingAction(ContractModel):
    id: str
    type: PendingActionType
    payload: dict[str, Any]
    status: PendingActionStatus = PendingActionStatus.PENDING
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    error_message: str | None = None


class ChatRequest(ContractModel):
    session_id: str = Field(min_length=1, max_length=128)
    message: str = Field(min_length=1, max_length=4000)


class ChatResponse(ContractModel):
    reply: str
    pending_action: PendingAction | None = None


class InvoiceListResponse(ContractModel):
    invoices: list[Invoice]


class Insights(ContractModel):
    outstanding: Decimal = Decimal("0.00")
    paid_this_month: Decimal = Decimal("0.00")
    overdue: Decimal = Decimal("0.00")


class ActionResponse(ContractModel):
    action: PendingAction
    invoice: Invoice | None = None
