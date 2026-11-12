# Quality scorecard

| Area | Initial grade | Current grade | Target | Notes |
|---|---:|---:|---:|---|
| Contract and validation | D | B | A | Shared Pydantic contract retained; schema tests pass. |
| Confirmation safety | F | B | A | SQLite action transition is guarded; demo creation and provider operations occur only after confirm. |
| PayPal sandbox integration | F | B | B | Sandbox-only HTTP adapter with mocked tests; real credential smoke test remains manual. |
| Agent behavior | F | B | B | Optional Claude/LangGraph structured drafting with validation; representative prompt evaluation remains. |
| UI and accessibility | F | C | B | Chat/dashboard, status labels, and visible approval controls implemented; browser review remains. |
| Tests and docs | F | B | B | API/schema checks and demo documentation added. |

## Current limits

Demo mode uses fictional local data and makes no network calls. Claude mode sends chat text to Anthropic and requires an API key. Sandbox mode requires PayPal credentials and has not had a live smoke test. Automated prompt evaluations remain incomplete. No production mode exists.
