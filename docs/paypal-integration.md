# PayPal Sandbox integration

InvoicePilot supports an offline local demo by default. To enable PayPal Sandbox, set `DEMO_MODE=false`, `PAYPAL_ENVIRONMENT=sandbox`, and provide `PAYPAL_CLIENT_ID` and `PAYPAL_CLIENT_SECRET` in an ignored local `.env` file. Startup rejects missing credentials and any non-sandbox environment.

Invoice creation uses `POST /v2/invoicing/invoices`, followed by `POST /v2/invoicing/invoices/{id}/send`. Both calls use deterministic `PayPal-Request-Id` values derived from the pending action. Provider operations run only from the confirmed action dispatcher. Status refresh calls `GET /v2/invoicing/invoices/{id}`. Reminder and cancellation actions require a local invoice with a linked PayPal invoice ID and an explicit confirmation.

Provider errors are returned as a generic API error; action records retain an inspectable failure state. Do not retry a failed or ambiguous action by creating a new action: inspect the Sandbox invoice first and use the original action/request IDs where a retry is appropriate.

The adapter is tested with HTTPX mocks. A real Sandbox smoke test is manual and requires credentials from a PayPal developer Sandbox app. It is not run automatically.

References: [PayPal Invoicing v2 API](https://developer.paypal.com/api/invoicing/v2/), [Create draft invoice](https://developer.paypal.com/api/invoicing/v2/invoices-create/), [Send invoice](https://developer.paypal.com/api/invoicing/v2/invoices-send/), [Show invoice details](https://developer.paypal.com/api/invoicing/v2/invoices-get/), and [Cancel sent invoice](https://developer.paypal.com/api/invoicing/v2/invoices-cancel/).
