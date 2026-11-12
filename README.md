# InvoicePilot

InvoicePilot helps freelancers turn chat requests into reviewable invoice drafts, track invoices, and send through PayPal Sandbox after explicit human confirmation. The app includes an offline demo agent and an optional Claude-backed LangGraph agent.

## Quick start

Requirements: Python 3.12.

```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\python -m pip install -r requirements.lock.txt
Copy-Item .env.example .env
.\.venv\Scripts\python -m uvicorn app.main:app --reload
```

In a second PowerShell window:

```powershell
.\.venv\Scripts\python -m streamlit run ui/streamlit_app.py
```

Open `http://localhost:8501`. The API health endpoint is `http://127.0.0.1:8000/health`.

## Agent modes

- **Offline demo (default):** keep `DEMO_MODE=true` and `AGENT_MODE=demo`. This uses a deterministic parser and fictional local invoices. No AI or PayPal network calls are made.
- **Claude drafting:** set `AGENT_MODE=claude`, `ANTHROPIC_API_KEY`, and optionally `ANTHROPIC_MODEL`. The LangGraph workflow sends the chat request to Claude and asks for a structured invoice draft or a follow-up question. Claude has no PayPal tools and cannot execute provider operations.
- **PayPal Sandbox:** set `DEMO_MODE=false`, provide `PAYPAL_CLIENT_ID` and `PAYPAL_CLIENT_SECRET`, and keep `PAYPAL_ENVIRONMENT=sandbox`. Provider operations are available only after the user confirms a pending action. Production endpoints are rejected.

Claude mode sends chat text to Anthropic for processing. Do not enter sensitive or real customer data in a demo or hackathon run.

## Tests

```powershell
.\.venv\Scripts\python -m pytest -q
```

Tests use local SQLite and mocked model/provider calls; they do not contact Anthropic or PayPal.

## Architecture and safety

Streamlit calls FastAPI, which stores invoices, chat history, and pending actions in SQLite. The agent can only return a validated draft; the API stores it as `PENDING`. Only the explicit confirmation route calls PayPal Sandbox. See [the specification](specs/invoicepilot.md), [PayPal integration notes](docs/paypal-integration.md), and [the demo walkthrough](docs/demo-script.md).

## License

Released under the MIT License. See [LICENSE](LICENSE).
