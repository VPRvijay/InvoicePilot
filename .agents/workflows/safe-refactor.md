# Safe refactoring workflow

1. Keep current behavior pinned with tests before changing structure.
2. Refactor one module at a time; do not change the shared API contract in the same increment.
3. Run the focused and full test suites after each behavior-preserving change.
4. Review the diff for accidental secrets and confirm no PayPal call moved into an LLM tool.
