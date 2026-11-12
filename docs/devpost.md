# Devpost Submission Copy — InvoicePilot

## Tagline

Turn a freelancer's chat request into a reviewable invoice draft, then send through PayPal Sandbox only after explicit approval.

## Project description

InvoicePilot is a chat-based invoicing assistant for freelancers. It extracts invoice details from a request, asks follow-up questions when required information is missing, and prepares a structured draft for review. The dashboard tracks outstanding, paid, and overdue invoices.

The app includes two agent modes. The offline demo uses a deterministic parser and fictional invoice data. The optional Claude mode runs a LangGraph workflow with structured output to draft invoices or ask for missing details. In both modes, the model can only propose a draft: FastAPI validates it and records it as a pending action. A person must confirm that action before the application sends an invoice through PayPal Sandbox.

PayPal integration uses the Invoicing API in Sandbox mode. The app rejects production endpoints. Automated tests mock the PayPal and Claude boundaries; a live PayPal Sandbox run requires developer credentials and has not been verified as part of the automated suite.

## Technology

- Python, FastAPI, SQLite, and Streamlit
- LangGraph, LangChain Anthropic, and Claude in optional AI mode
- PayPal Invoicing API v2 Sandbox
- Pydantic validation and pytest

## Run the demo

See [README.md](../README.md) for installation and configuration. The default demo runs offline with fictional data. To demonstrate Claude drafting, configure `AGENT_MODE=claude` and `ANTHROPIC_API_KEY`. To demonstrate provider operations, configure PayPal Sandbox credentials and `DEMO_MODE=false`.

## Safety

No credentials are included in the repository. The `.env` file and local database are ignored by Git. The model has no provider tools; only a human-confirmed pending action can reach the PayPal Sandbox adapter.
