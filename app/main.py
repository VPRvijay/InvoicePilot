from __future__ import annotations

import os
from contextlib import asynccontextmanager
from datetime import date
from fastapi import FastAPI, HTTPException
from dotenv import load_dotenv

load_dotenv()

from app import db
from app.agent.demo import DemoAgent, create_demo_invoice, draft_action
from app.agent.claude import ClaudeAgent
from app.schemas import ActionResponse, ChatRequest, ChatResponse, Insights, Invoice, InvoiceDraft, InvoiceListResponse, InvoiceStatus, PendingActionStatus, PendingActionType
from app.paypal_client import PayPalAPIError, PayPalClient, map_provider_status


@asynccontextmanager
async def lifespan(app: FastAPI):
    if os.getenv("DEMO_MODE", "true").lower() != "true":
        if os.getenv("PAYPAL_ENVIRONMENT", "sandbox").lower() != "sandbox":
            raise RuntimeError("Only PayPal Sandbox is supported")
        if not os.getenv("PAYPAL_CLIENT_ID") or not os.getenv("PAYPAL_CLIENT_SECRET"):
            raise RuntimeError("PayPal Sandbox credentials are required when DEMO_MODE=false")
    agent_mode = os.getenv("AGENT_MODE", "demo").lower()
    if agent_mode not in {"demo", "claude"}:
        raise RuntimeError("AGENT_MODE must be demo or claude")
    if agent_mode == "claude" and not os.getenv("ANTHROPIC_API_KEY"):
        raise RuntimeError("ANTHROPIC_API_KEY is required when AGENT_MODE=claude")
    db.initialize()
    yield

app = FastAPI(title="InvoicePilot Demo", version="0.1.0", lifespan=lifespan)
def _provider() -> PayPalClient:
    return PayPalClient(os.environ["PAYPAL_CLIENT_ID"], os.environ["PAYPAL_CLIENT_SECRET"], environment=os.getenv("PAYPAL_ENVIRONMENT", "sandbox"))


def _invoice_agent():
    if os.getenv("AGENT_MODE", "demo").lower() == "claude":
        return ClaudeAgent(
            api_key=os.getenv("ANTHROPIC_API_KEY"),
            model_name=os.getenv("ANTHROPIC_MODEL", "claude-sonnet-4-6"),
        )
    return DemoAgent()


@app.get("/health")
def health():
    demo_mode = os.getenv("DEMO_MODE", "true").lower() == "true"
    return {"status": "ok", "mode": "demo" if demo_mode else "sandbox", "provider": "local" if demo_mode else "paypal_sandbox"}


@app.post("/chat", response_model=ChatResponse)
def chat(request: ChatRequest):
    question = request.message.lower()
    if any(term in question for term in ("outstanding", "overdue", "paid this month", "list invoices", "show invoices", "insight")):
        totals = db.insights()
        if "overdue" in question:
            reply = f"Local demo invoices overdue: {totals['overdue']} USD."
        elif "paid" in question:
            reply = f"Local demo invoices paid this month: {totals['paid_this_month']} USD."
        elif "list" in question or "show" in question:
            rows = db.list_invoices()
            reply = "Local demo invoices: " + "; ".join(f"{item.draft.client_name} ({item.status.value}, {item.total} {item.draft.currency})" for item in rows)
        else:
            reply = f"Local demo outstanding: {totals['outstanding']} USD; overdue: {totals['overdue']} USD; paid this month: {totals['paid_this_month']} USD."
        draft = None
    else:
        reply, draft = _invoice_agent().respond(request.message)
    action = draft_action(draft) if draft else None
    if action:
        db.save_action(action)
    db.log_chat(request.session_id, request.message, reply)
    return ChatResponse(reply=reply, pending_action=action)


@app.get("/invoices", response_model=InvoiceListResponse)
def invoices():
    return InvoiceListResponse(invoices=db.list_invoices())


@app.get("/invoices/{invoice_id}", response_model=Invoice)
def invoice(invoice_id: str):
    result = db.get_invoice(invoice_id)
    if not result:
        raise HTTPException(404, "Invoice not found")
    return result


@app.post("/invoices/{invoice_id}/refresh", response_model=Invoice)
def refresh(invoice_id: str):
    result = db.get_invoice(invoice_id)
    if not result:
        raise HTTPException(404, "Invoice not found")
    if result.paypal_invoice_id and os.getenv("DEMO_MODE", "true").lower() != "true":
        provider = _provider()
        try:
            provider_data = provider.get_invoice(result.paypal_invoice_id)
        finally:
            provider.close()
        provider_status = str(provider_data.get("status", "UNKNOWN"))
        result.provider_status = provider_status
        result.status = InvoiceStatus(map_provider_status(provider_status))
    if result.status == "SENT" and result.due_date < date.today():
        result.status = InvoiceStatus.OVERDUE
        if not result.paypal_invoice_id:
            result.provider_status = "DEMO_OVERDUE"
        db.save_invoice(result)
    return result


@app.get("/insights", response_model=Insights)
def get_insights():
    return Insights(**db.insights())


@app.post("/actions/{action_id}/confirm", response_model=ActionResponse)
def confirm(action_id: str):
    action = db.transition_action(action_id, PendingActionStatus.PENDING, PendingActionStatus.EXECUTING)
    if not action:
        existing = db.get_action(action_id)
        if not existing:
            raise HTTPException(404, "Pending action not found")
        raise HTTPException(409, f"Action is {existing.status.value.lower()}")
    try:
        demo_mode = os.getenv("DEMO_MODE", "true").lower() == "true"
        if action.type == PendingActionType.CREATE_AND_SEND_INVOICE:
            draft = InvoiceDraft.model_validate(action.payload["draft"])
            if demo_mode:
                result = create_demo_invoice(draft)
            else:
                provider = _provider()
                try:
                    provider_id = provider.create_and_send(draft, action.id)
                finally:
                    provider.close()
                result = create_demo_invoice(draft)
                result.id = f"invoice-{action.id}"
                result.paypal_invoice_id = provider_id
                result.provider_status = "SENT"
            db.save_invoice(result)
            confirmed = db.transition_action(action_id, PendingActionStatus.EXECUTING, PendingActionStatus.CONFIRMED)
            return ActionResponse(action=confirmed, invoice=result)
        if action.type in (PendingActionType.CANCEL_INVOICE, PendingActionType.SEND_REMINDER):
            if demo_mode:
                raise RuntimeError("This action is unavailable in demo mode")
            invoice_id = action.payload.get("invoice_id")
            local = db.get_invoice(invoice_id or "")
            if not local or not local.paypal_invoice_id:
                raise RuntimeError("A linked PayPal Sandbox invoice is required")
            provider = _provider()
            try:
                if action.type == PendingActionType.CANCEL_INVOICE:
                    provider.cancel_invoice(local.paypal_invoice_id, action.id)
                    local.status = InvoiceStatus.CANCELLED
                    local.provider_status = "CANCELLED"
                    db.save_invoice(local)
                else:
                    provider.send_reminder(local.paypal_invoice_id, action.id)
            finally:
                provider.close()
            confirmed = db.transition_action(action_id, PendingActionStatus.EXECUTING, PendingActionStatus.CONFIRMED)
            return ActionResponse(action=confirmed, invoice=local if action.type == PendingActionType.CANCEL_INVOICE else None)
        raise RuntimeError("Unsupported action type")
    except Exception as exc:
        failed = db.transition_action(action_id, PendingActionStatus.EXECUTING, PendingActionStatus.FAILED, str(exc)[:500])
        detail = str(exc) if isinstance(exc, PayPalAPIError) else "Could not process action; inspect the failed action before retrying"
        raise HTTPException(422, detail) from exc


@app.post("/actions/{action_id}/cancel", response_model=ActionResponse)
def cancel(action_id: str):
    action = db.transition_action(action_id, PendingActionStatus.PENDING, PendingActionStatus.CANCELLED)
    if not action:
        existing = db.get_action(action_id)
        if not existing:
            raise HTTPException(404, "Pending action not found")
        raise HTTPException(409, f"Action is {existing.status.value.lower()}")
    return ActionResponse(action=action)
