# InvoicePilot MVP specification

## Goal
Help freelancers draft PayPal invoices from natural language, review them before sending, and track payment status in a dashboard.

## Scope
- Chat-based invoice drafting, with questions for missing client email, amount, line items, currency, or due date.
- Human-approved invoice creation and sending through PayPal Sandbox.
- Local invoice persistence, manual refresh plus lightweight polling, and dashboard totals.
- Read-only answers for invoices and insights, plus editable follow-up drafts and a confirmed reminder action.

## Safety requirements
- The agent never calls a PayPal write operation. It can return a validated draft or create a local `PendingAction` only.
- A visible confirmation click is required for invoice send, reminder, or cancellation actions.
- No operation can run twice after an action has left `PENDING`.
- Only sandbox endpoints are allowed. Secrets must not be committed.

## Shared models
- `InvoiceDraft`: `client_name`, `client_email`, `items` (`description`, positive `quantity`, non-negative `unit_price`), `currency`, positive `due_in_days`, optional `note`.
- `Invoice`: local `id`, nullable `paypal_invoice_id`, `draft`, status (`DRAFT`, `SENT`, `PAID`, `OVERDUE`, `CANCELLED`), `total`, `created_at`, `due_date`, optional `paid_at`.
- `PendingAction`: `id`, type (`create_and_send_invoice`, `cancel_invoice`, `send_reminder`), JSON-compatible `payload`, status (`PENDING`, `EXECUTING`, `CONFIRMED`, `CANCELLED`, `FAILED`). `EXECUTING` and `FAILED` are added so retries and concurrent confirmations cannot silently repeat provider side effects.
- `POST /chat`: accepts `session_id` and `message`; returns `reply` and optional `pending_action`.
- `POST /actions/{id}/confirm` and `/cancel`.
- `GET /invoices`, `GET /invoices/{id}`, `POST /invoices/{id}/refresh`.
- `GET /insights`: outstanding, paid this month, overdue.
- `GET /health`.

## Agent behavior
The LangGraph agent uses Claude and only local tools: `draft_invoice` creates a pending action, `list_invoices` and `get_insights` read local data, `draft_followup` creates editable text, and `propose_reminder` creates a pending action. The model must ask for missing details and must never claim an invoice was sent unless the API confirms it.

## PayPal adapter
Use v2 Invoicing endpoints in sandbox mode. The confirmed invoice action creates a draft, then sends it. Status refresh retrieves provider state and derives `OVERDUE` from the local due date. Reminder and cancellation are only reachable through confirmed actions. If provider state is ambiguous after a timeout, do not report success; retain an inspectable failed action and use the same request ID for safe retry where supported.

## Acceptance
A fresh environment can run the API and UI; schema tests pass; no provider write occurs before confirmation; cancel drops a pending action without a provider call; confirmation sends exactly once; status mapping, dashboard totals, and read-only chat behavior are tested. Sandbox credentials are needed only for the real-provider smoke test.


## Offline demo behavior (default)
- `DEMO_MODE=true` uses the deterministic local parser and seeded fictional invoices.
- A deterministic local parser replaces Claude. It can only create a `PENDING` local invoice action after required fields are present.
- SQLite is seeded with fictional invoices spanning `SENT`, `PAID`, `OVERDUE`, and `DRAFT`; refresh and insights operate on local state.
- Explicit confirmation creates a local invoice marked `SENT`. It does not call PayPal or create a real invoice. Cancel leaves invoice data unchanged.

## PayPal Sandbox mode
- `DEMO_MODE=false` requires PayPal credentials and `PAYPAL_ENVIRONMENT=sandbox`; other environments fail startup.
- Invoice send, reminder, and cancellation operations are called only by the explicit confirm endpoint, and only for a still-pending action.

## Claude drafting mode
- `AGENT_MODE=claude` requires `ANTHROPIC_API_KEY`; `ANTHROPIC_MODEL` selects the model and defaults to `claude-sonnet-4-6`.
- The LangGraph workflow uses structured output to return a validated `InvoiceDraft` or a follow-up reply. It has no provider tools and cannot perform external actions.
- The API stores a returned draft as a `PENDING` action. The existing explicit confirmation route remains the only route to a PayPal write operation.
- `AGENT_MODE=demo` is the default and makes no Anthropic calls. Automated tests mock the model boundary.
