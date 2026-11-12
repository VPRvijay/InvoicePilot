from __future__ import annotations

import re
from datetime import UTC, date, datetime, timedelta
from decimal import Decimal
from uuid import uuid4

from app.schemas import Invoice, InvoiceDraft, InvoiceDraftItem, InvoiceStatus, PendingAction, PendingActionType


class DemoAgent:
    """Deterministic, offline invoice intent parser. It only drafts local actions."""
    def respond(self, message: str) -> tuple[str, InvoiceDraft | None]:
        email = re.search(r"[\w.+-]+@[\w.-]+\.[A-Za-z]{2,}", message)
        amount = re.search(r"(?:\$|USD\s*)(\d+(?:\.\d{1,2})?)", message, re.I)
        name_match = re.search(r"(?:invoice|bill)\s+(?:for\s+)?([A-Z][A-Za-z]+(?:\s+[A-Z][A-Za-z]+)?)", message, re.I)
        missing = []
        if not name_match: missing.append("client name")
        if not email: missing.append("client email")
        if not amount: missing.append("amount")
        description = "Professional services"
        if amount:
            description_text = message[amount.end():]
            description_text = re.sub(r"^\s*(?:for|of)\s+", "", description_text, flags=re.I)
            description_text = re.sub(r"\s+due\s+in\s+\d+\s+days?\s*$", "", description_text, flags=re.I)
            description_text = description_text.strip(" ,.")
            if description_text:
                description = description_text
        if not description or description.lower() in {"days", "day"}: description = "Professional services"
        if missing:
            return f"I need the {' and '.join(missing)} before I can prepare a draft.", None
        due_match = re.search(r"due\s+in\s+(\d+)\s+days?", message, re.I)
        due = int(due_match.group(1)) if due_match else 30
        draft = InvoiceDraft(client_name=name_match.group(1), client_email=email.group(0), items=[InvoiceDraftItem(description=description[:200], quantity=1, unit_price=Decimal(amount.group(1)))], due_in_days=due)
        return f"I prepared a local draft for {draft.client_name} totaling {draft.currency} {draft.total}. Review it and confirm below to simulate sending.", draft


def create_demo_invoice(draft: InvoiceDraft) -> Invoice:
    now = datetime.now(UTC)
    return Invoice(id=f"demo-{uuid4().hex[:10]}", draft=draft, status=InvoiceStatus.SENT, total=draft.total, created_at=now, due_date=date.today() + timedelta(days=draft.due_in_days), provider_status="DEMO_SENT")


def draft_action(draft: InvoiceDraft) -> PendingAction:
    return PendingAction(id=f"action-{uuid4().hex[:10]}", type=PendingActionType.CREATE_AND_SEND_INVOICE, payload={"draft": draft.model_dump(mode="json")})
