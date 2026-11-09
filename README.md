# InvoicePilot

InvoicePilot helps freelancers turn a short chat request into a PayPal invoice draft, review it, and send it only after explicit confirmation. It tracks sandbox invoice status in a simple dashboard.

## Status

The project is being built for the PayPal AI Hackathon. PayPal production mode is intentionally unsupported. See `specs/invoicepilot.md` for the behavior contract and `AGENTS.md` for project commands and agent rules.

## Run locally

1. Install Python 3.12.
2. Create an environment and install packages:

   ```powershell
   py -3.12 -m venv .venv
   .\.venv\Scripts\python -m pip install -r requirements.txt
   Copy-Item .env.example .env
   ```

3. Keep `DEMO_MODE=true` for the local fake-provider flow, or set it to `false` and provide `ANTHROPIC_API_KEY`, `PAYPAL_CLIENT_ID`, and `PAYPAL_CLIENT_SECRET` from your PayPal Developer Sandbox app.
4. Start the API and UI in separate PowerShell windows:

   ```powershell
   .\.venv\Scripts\python -m uvicorn app.main:app --reload
   .\.venv\Scripts\python -m streamlit run ui/streamlit_app.py
   ```

5. Open Streamlit at `http://localhost:8501`. The API health check is `http://127.0.0.1:8000/health`.

## Test

```powershell
.\.venv\Scripts\python -m pytest -q
```

Automated tests mock PayPal and Claude. A real sandbox smoke test requires sandbox credentials and is run manually. Never use production credentials.

## Architecture

Streamlit calls the FastAPI backend. FastAPI stores invoices, chat history, and pending actions in SQLite. The LangGraph agent can only draft a local pending action and read local invoice data. The confirmation endpoint alone calls PayPal's sandbox Invoicing API.

PayPal's Python Agent Toolkit currently pins an older LangChain release. This project uses PayPal's documented v2 REST API through HTTPX to keep the current LangGraph stack compatible and to limit outbound actions to a small server-controlled adapter. Official references are in `docs/paypal-integration.md`.

## Environment variables

| Name | Purpose |
|---|---|
| `DEMO_MODE` | Use local deterministic agent/provider behavior without external keys. |
| `DATABASE_PATH` | SQLite file path. |
| `ANTHROPIC_API_KEY` | Claude API key when demo mode is off. |
| `ANTHROPIC_MODEL` | Claude model identifier. |
| `PAYPAL_CLIENT_ID`, `PAYPAL_CLIENT_SECRET` | PayPal Sandbox app credentials. |
| `PAYPAL_ENVIRONMENT` | Must remain `sandbox`. |
| `POLL_INTERVAL_SECONDS` | Background status-poll cadence. |
| `CORS_ORIGINS` | Allowed local UI origins. |
| `API_BASE_URL` | FastAPI base URL used by Streamlit. |

## Tools used

Python, FastAPI, SQLite, Streamlit, LangGraph, Claude via LangChain Anthropic, and PayPal Invoicing v2 Sandbox.
