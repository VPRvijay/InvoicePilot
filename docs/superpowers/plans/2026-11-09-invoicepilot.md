# InvoicePilot implementation plan

> **For agentic workers:** Use the LobeHub task lanes below for research and module drafts. Codex owns repository writes and integration.

**Goal:** Build an MVP that drafts, confirms, sends, and tracks PayPal sandbox invoices for freelancers.

**Architecture:** Streamlit calls a FastAPI service backed by SQLite. A LangGraph/Claude agent can only draft local actions and query read-only application data. The confirm route alone invokes the sandbox PayPal adapter.

**Tech Stack:** Python 3.12, FastAPI, Pydantic v2, SQLite, HTTPX, Streamlit, LangGraph, LangChain Anthropic, PayPal v2 Invoicing REST API.

**Spec:** `specs/invoicepilot.md`

## Global Constraints
- Keep all PayPal calls in Sandbox; block production configuration.
- Never commit `.env` or API keys.
- The model cannot call PayPal write operations.
- The UI must require an explicit click to confirm or cancel a pending action.
- Keep the API contract in `specs/invoicepilot.md` stable.
- Only Codex writes repository files; Gemini and Kernel return bounded research/drafts in LobeHub.

## Review Focus
- Missing invoice fields: ask instead of guessing and do not create an action.
- Concurrent/repeated confirm requests: only one may transition a pending action to execution.
- Provider timeout after a write: don't claim success or create duplicate invoices on retry.
- Unknown provider status: don't mark it paid or overdue without evidence.
- Missing secrets/network: keep local demo/tests usable and return a clear, sanitized error.

---

### Task 1: Scaffold and shared contract

**Files:** `AGENTS.md`, `specs/invoicepilot.md`, `app/schemas.py`, `tests/test_schemas.py`, `.gitignore`, `requirements.txt`, `README.md`, `.env.example`.

- [ ] Write and run failing schema tests for required fields, valid items, positive quantity/due date, currency, statuses, and PendingAction types.
- [ ] Implement the Pydantic models from the spec and validate serialized JSON round trips.
- [ ] Add environment setup, sandbox-only config, readme, license, and ignore rules.

### Task 2: SQLite and confirmation API

**Files:** `app/db.py`, `app/main.py`, `app/paypal_client.py`, `tests/test_api.py`, `tests/test_db.py`.

- [ ] Test the action state transition, duplicate confirm prevention, cancel behavior, invoice CRUD, insights aggregation, health, and due-date status mapping with a fake PayPal adapter.
- [ ] Implement parameterized SQLite repositories and a temporary-database override for tests.
- [ ] Implement the API contract and keep provider writes behind the confirmed action dispatcher.
- [ ] Add periodic sandbox status polling with a short configurable interval and clean shutdown.

### Task 3: PayPal Sandbox adapter

**Owner in LobeHub:** Gemini (research/module draft); Codex integrates.

**Files:** `app/paypal_client.py`, `tests/test_paypal_client.py`, `docs/paypal-integration.md`.

- [ ] Verify v2 endpoints and payloads against current official PayPal docs.
- [ ] Test request mapping, OAuth failure, provider error sanitization, and status mapping using HTTPX mocks.
- [ ] Implement OAuth caching, request IDs, draft-create/send pair, fetch, reminder, and cancel operations using the sandbox base URL only.
- [ ] Keep the external sandbox smoke test documented and manual.

### Task 4: Agent and evaluation

**Owner in LobeHub:** Kernel (agent/quality draft); Codex integrates.

**Files:** `app/agent/graph.py`, `app/agent/tools.py`, `app/agent/prompts.py`, `tests/test_agent_eval.py`.

- [ ] Test that drafting returns local PendingAction data and never calls PayPal.
- [ ] Implement graph with Claude, bounded tool loop, and only local read/draft tools.
- [ ] Add ten prompt cases with expected action type, required clarification, and no-send behavior.

### Task 5: Streamlit dashboard and docs

**Files:** `ui/streamlit_app.py`, `tests/test_ui.py`, `README.md`, `docs/demo-script.md`, `docs/devpost.md`.

- [ ] Test Streamlit rendering for empty state, invoice table, approval card, and errors.
- [ ] Implement a chat-left/dashboard-right layout with explicit Send/Cancel buttons.
- [ ] Add editable follow-up drafts, refresh controls, setup docs, Devpost text, and a 2:30 demo script.
- [ ] Run the full suite and perform a fresh-clone/manual local flow review.

## Parallel coordination
After Task 1 is committed, create two LobeHub tasks: Gemini owns the PayPal research/draft; Kernel owns the agent/evaluation draft. Both receive this spec and contract. Codex integrates only after both outputs are reviewed. Keep commits small and update this checklist as work completes.
