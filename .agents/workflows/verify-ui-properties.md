# UI verification workflow

Run the Streamlit app against the local API and inspect these flows:

- Empty invoice list and dashboard summary.
- Chat creates a draft card only; no PayPal request occurs.
- Send and Cancel buttons are visibly separate and require a click.
- Cancel removes the pending action without a provider write.
- Confirm shows a sent invoice only after the API confirms success.
- Refresh updates status and totals; API errors are shown without stack traces.
- Narrow viewport keeps chat input and action buttons usable.
