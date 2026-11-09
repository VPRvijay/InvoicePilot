# Testing strategy

- Unit tests cover Pydantic validation, totals/status mapping, pending-action state transitions, and safe agent tool outputs.
- API tests use FastAPI TestClient and temporary SQLite databases. PayPal and Claude calls are replaced with deterministic fakes.
- Integration tests prove there is no PayPal write call before confirmation and that one confirmed action executes at most once.
- Agent evaluation contains ten representative prompts and asserts expected action types/required clarifying questions, not exact prose.
- A manual sandbox smoke test is separate from the automated suite and must never use production credentials.
- The final manual UI pass follows the README: draft, inspect, cancel; then draft, confirm, refresh status.
