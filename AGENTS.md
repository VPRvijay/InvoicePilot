# InvoicePilot Agent Guide

## Non-negotiable rules
- Read `specs/invoicepilot.md` before changing application behavior.
- Keep PayPal in sandbox mode. Never commit `.env`, API credentials, or customer secrets.
- The LLM may only draft a `PendingAction`; only an explicit confirm endpoint may call an outbound PayPal operation.
- Preserve the shared models and HTTP contract in the spec. Route contract changes through the integration owner.
- Keep each change small, add a focused test first, run it, then run the full suite after integration.

## Repository map
- `app/schemas.py`: public Pydantic models and enums.
- `app/db.py`: SQLite schema and repositories.
- `app/main.py`: FastAPI application, API routes, confirmation gate, status polling.
- `app/paypal_client.py`: sandbox-only PayPal Invoicing API adapter.
- `app/agent/`: Claude/LangGraph behavior and safe, local-only tools.
- `ui/streamlit_app.py`: chat and invoice dashboard.
- `tests/`: unit and API tests; external PayPal calls must be mocked unless a human runs a sandbox smoke test.
- `specs/invoicepilot.md`: product and interface contract.
- `docs/architecture.md`: system map and design choices.
- `docs/superpowers/plans/2026-11-09-invoicepilot.md`: implementation plan.
- `TODO.md`: current phase and remaining work.

## Local commands (PowerShell)
- Create environment: `py -3.12 -m venv .venv`
- Install: `.\.venv\Scripts\python -m pip install -r requirements.txt`
- API: `.\.venv\Scripts\python -m uvicorn app.main:app --reload`
- UI: `.\.venv\Scripts\python -m streamlit run ui/streamlit_app.py`
- Tests: `.\.venv\Scripts\python -m pytest -q`

## Working agreements
- Use the project root as the working directory.
- Gemini's assigned lane researches PayPal and returns a source-backed module draft; Kernel's lane drafts the agent and quality work. Codex integrates all repository writes.
- Do not overlap edits. Keep API request/response shapes stable after the schema checkpoint.
- Update `TODO.md`, `docs/quality.md`, and the relevant spec when a phase changes project behavior.
