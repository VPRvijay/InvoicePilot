# Core beliefs

- The written contract is the shared memory for Codex, Gemini, and Kernel.
- External services and model outputs are untrusted; validate their data at the boundary.
- A user confirmation is a hard boundary: agent planning never calls PayPal.
- Prefer a small, runnable vertical slice over broad scaffolding without behavior.
- Keep secrets outside version control and keep PayPal in sandbox mode.
- Make tests describe user-visible behavior, especially the confirmation gate.
