# Quality scorecard

| Area | Initial grade | Target | Notes |
|---|---:|---:|---|
| Contract and validation | D | A | Pin shared schemas with unit tests. |
| Confirmation safety | F | A | No PayPal write operation before explicit confirmation. |
| PayPal sandbox integration | F | B | Verify credentials and real sandbox behavior manually. |
| Agent behavior | F | B | Evaluate missing details, safe drafts, and read-only questions. |
| UI and accessibility | F | B | Review chat, approval card, dashboard, and errors. |
| Tests and docs | F | B | Mock external services; fresh-clone README check. |

No domain is production-ready until reviewed and tested against its target behavior.
