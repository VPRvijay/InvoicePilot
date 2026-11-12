from __future__ import annotations

import json
import os
import sqlite3
from contextlib import contextmanager
from datetime import UTC, date, datetime, timedelta
from decimal import Decimal
from pathlib import Path
from uuid import uuid4

from app.schemas import Invoice, InvoiceDraft, InvoiceStatus, PendingAction, PendingActionStatus

DATABASE_PATH = os.getenv("DATABASE_PATH", "data/invoicepilot.db")


@contextmanager
def connect():
    path = Path(DATABASE_PATH)
    path.parent.mkdir(parents=True, exist_ok=True)
    connection = sqlite3.connect(path, timeout=10, isolation_level=None)
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA journal_mode=WAL")
    try:
        yield connection
    finally:
        connection.close()


def initialize() -> None:
    with connect() as con:
        con.executescript("""
        CREATE TABLE IF NOT EXISTS invoices (id TEXT PRIMARY KEY, data TEXT NOT NULL);
        CREATE TABLE IF NOT EXISTS actions (id TEXT PRIMARY KEY, data TEXT NOT NULL);
        CREATE TABLE IF NOT EXISTS chats (id INTEGER PRIMARY KEY AUTOINCREMENT, session_id TEXT, message TEXT, reply TEXT, created_at TEXT);
        """)
        if os.getenv("DEMO_MODE", "true").lower() == "true" and con.execute("SELECT COUNT(*) FROM invoices").fetchone()[0] == 0:
            _seed(con)


def _seed(con: sqlite3.Connection) -> None:
    today = date.today()
    samples = [
        ("Jordan Lee", "jordan@example.com", "Brand identity design", 1, "850.00", InvoiceStatus.SENT, today + timedelta(days=8)),
        ("Mina Patel", "mina@example.com", "Website copywriting", 3, "240.00", InvoiceStatus.PAID, today - timedelta(days=4)),
        ("Northstar Studio", "ap@northstar.example.com", "Monthly consulting", 2, "600.00", InvoiceStatus.OVERDUE, today - timedelta(days=5)),
        ("Cedar Works", "finance@cedar.example.com", "Prototype review", 1, "375.00", InvoiceStatus.DRAFT, today + timedelta(days=15)),
    ]
    for name, email, description, quantity, price, status, due in samples:
        draft = InvoiceDraft(client_name=name, client_email=email, items=[{"description": description, "quantity": quantity, "unit_price": price}], due_in_days=max(1, (due-today).days))
        inv = Invoice(id=f"demo-{uuid4().hex[:8]}", draft=draft, status=status, total=draft.total, due_date=due, created_at=datetime.now(UTC) - timedelta(days=15), paid_at=datetime.now(UTC) - timedelta(days=4) if status == InvoiceStatus.PAID else None)
        con.execute("INSERT INTO invoices VALUES (?, ?)", (inv.id, inv.model_dump_json()))


def list_invoices() -> list[Invoice]:
    initialize()
    with connect() as con:
        return [Invoice.model_validate_json(r[0]) for r in con.execute("SELECT data FROM invoices ORDER BY rowid DESC")]


def get_invoice(invoice_id: str) -> Invoice | None:
    initialize()
    with connect() as con:
        row = con.execute("SELECT data FROM invoices WHERE id=?", (invoice_id,)).fetchone()
    return Invoice.model_validate_json(row[0]) if row else None


def save_invoice(invoice: Invoice) -> Invoice:
    initialize()
    with connect() as con:
        con.execute("INSERT OR REPLACE INTO invoices VALUES (?, ?)", (invoice.id, invoice.model_dump_json()))
    return invoice


def save_action(action: PendingAction) -> PendingAction:
    initialize()
    with connect() as con:
        con.execute("INSERT INTO actions VALUES (?, ?)", (action.id, action.model_dump_json()))
    return action


def get_action(action_id: str) -> PendingAction | None:
    initialize()
    with connect() as con:
        row = con.execute("SELECT data FROM actions WHERE id=?", (action_id,)).fetchone()
    return PendingAction.model_validate_json(row[0]) if row else None


def transition_action(action_id: str, expected: PendingActionStatus, new: PendingActionStatus, error: str | None = None) -> PendingAction | None:
    initialize()
    with connect() as con:
        con.execute("BEGIN IMMEDIATE")
        row = con.execute("SELECT data FROM actions WHERE id=?", (action_id,)).fetchone()
        if not row:
            con.rollback()
            return None
        action = PendingAction.model_validate_json(row[0])
        if action.status != expected:
            con.rollback()
            return None
        action.status = new
        action.error_message = error
        con.execute("UPDATE actions SET data=? WHERE id=?", (action.model_dump_json(), action_id))
        con.commit()
        return action


def log_chat(session_id: str, message: str, reply: str) -> None:
    initialize()
    with connect() as con:
        con.execute("INSERT INTO chats(session_id,message,reply,created_at) VALUES(?,?,?,?)", (session_id, message, reply, datetime.now(UTC).isoformat()))


def insights() -> dict[str, Decimal]:
    rows = list_invoices()
    month = date.today().replace(day=1)
    paid = sum((i.total for i in rows if i.status == InvoiceStatus.PAID and i.paid_at and i.paid_at.date() >= month), Decimal("0"))
    outstanding = sum((i.total for i in rows if i.status in (InvoiceStatus.SENT, InvoiceStatus.OVERDUE)), Decimal("0"))
    overdue = sum((i.total for i in rows if i.status == InvoiceStatus.OVERDUE), Decimal("0"))
    return {"outstanding": outstanding, "paid_this_month": paid, "overdue": overdue}
