# InvoicePilot execution checklist

## Phase 1 - Shared foundation
- [x] Repo scaffolding, environment config, schemas, and schema tests.
- [x] FastAPI/SQLite contract, local persistence, deterministic demo agent.

## Phase 2 - Demo milestone
- [x] Seeded demo invoices and status/insight simulation.
- [x] Pending action confirmation/cancel gate; no provider calls.
- [x] Streamlit chat and dashboard with explicit approval controls.
- [x] Demo setup, script, Devpost copy, and acceptance checks.
- [ ] Review Gemini PayPal adapter and Kernel agent drafts when accessible; integrate only behind confirmed executor.

## Phase 3 - Sandbox integration
- [x] Sandbox-only PayPal adapter and mocked provider tests.
- [x] Confirmed provider dispatcher, status refresh, and reminder/cancellation operations.
- [x] LangGraph/Claude structured invoice drafting; model has no provider tools.
- [ ] Prompt evaluation with representative fictional requests and adversarial inputs.
- [ ] Full fresh-clone review and manual local flow.
- [ ] Optional real Sandbox smoke test with user-supplied credentials.
