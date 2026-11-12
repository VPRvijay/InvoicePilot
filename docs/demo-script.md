# InvoicePilot demo walkthrough (about 2 minutes)

## Offline demo

1. **Context:** InvoicePilot turns chat requests into invoice drafts and tracks their status. This walkthrough uses fictional local data and makes no external API calls.
2. **Dashboard:** Show outstanding, paid this month, and overdue totals, then the seeded invoices with varied statuses.
3. **Draft:** Enter: `Invoice Acme Studio, billing@example.com, $125 for design audit due in 15 days`. In offline mode, the deterministic parser prepares a local draft.
4. **Approval:** Review the pending action and confirm the simulation. The local invoice appears as sent. Show that a second confirmation is rejected.
5. **Cancellation:** Prepare another draft and cancel it. Verify no invoice was added.
6. **Safety:** Point out that the draft remains pending until a person confirms it.

## Optional Claude and PayPal Sandbox walkthrough

For an AI-assisted run, set `AGENT_MODE=claude` and `ANTHROPIC_API_KEY`, then demonstrate Claude extracting line items or asking a follow-up question. For provider integration, set `DEMO_MODE=false` and provide PayPal Sandbox credentials. Review the pending action before confirming; the adapter is Sandbox-only. Keep test customer data fictional.

## Checks covered by automated tests

- `/health` reports demo mode and seeded demo invoices are local.
- Incomplete offline requests do not create pending actions.
- A complete draft remains `PENDING` until confirmation.
- Confirmation creates one local demo invoice; duplicate confirmation is rejected.
- Cancellation leaves invoice data unchanged.
- Claude draft output passes through the same structured validation and confirmation gate.
- PayPal Sandbox operations are mocked in tests and occur only after explicit confirmation.
