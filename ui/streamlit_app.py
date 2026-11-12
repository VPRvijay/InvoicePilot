from __future__ import annotations

import os
import uuid

import httpx
import pandas as pd
import streamlit as st
from dotenv import load_dotenv

load_dotenv()

API = os.getenv("API_BASE_URL", "http://127.0.0.1:8000")
DEMO_MODE = os.getenv("DEMO_MODE", "true").lower() == "true"
st.set_page_config(page_title="InvoicePilot Demo", page_icon="IN", layout="wide")
st.markdown("""
<style>
[data-testid="stAppViewContainer"] { background: #f5f7fa; }
[data-testid="stSidebar"] { background: #102b46; }
[data-testid="stSidebar"] [data-testid="stAlert"], [data-testid="stSidebar"] [data-testid="stAlert"] > div { background-color: #183653 !important; border-color: #31516f !important; }
[data-testid="stSidebar"] * { color: #eef5fb !important; }
.hero { padding: 1.2rem 1.5rem; background: #102b46; color: white; border-radius: 8px; margin-bottom: 1rem; }
.hero h1 { margin: 0; font-size: 1.8rem; }
</style>
""", unsafe_allow_html=True)

if "session_id" not in st.session_state:
    st.session_state.session_id = str(uuid.uuid4())
if "messages" not in st.session_state:
    st.session_state.messages = []


def api(method: str, path: str, **kwargs):
    try:
        response = httpx.request(method, f"{API}{path}", timeout=5, **kwargs)
        response.raise_for_status()
        return response.json()
    except httpx.HTTPStatusError as exc:
        try:
            detail = exc.response.json().get("detail")
        except (ValueError, AttributeError):
            detail = None
        st.error(f"API error ({exc.response.status_code}): {detail or 'The request failed.'}")
        return None
    except httpx.HTTPError as exc:
        st.error(f"API unavailable: {exc}")
        return None


mode_label = "Local demo mode" if DEMO_MODE else "PayPal Sandbox mode"
st.markdown(f'<div class="hero"><h1>InvoicePilot</h1><div>Invoice assistant | {mode_label}</div></div>', unsafe_allow_html=True)
st.sidebar.info("DEMO MODE: no PayPal connection or provider calls." if DEMO_MODE else "SANDBOX MODE: confirmations call PayPal Sandbox only.")
left, right = st.columns([0.95, 1.25], gap="large")

with left:
    st.subheader("Prepare an invoice")
    st.caption("Example: Invoice Acme, billing@acme.com, $125 for design due in 15 days")
    for entry in st.session_state.messages:
        with st.chat_message(entry["role"]):
            st.write(entry["content"])
            pending = entry.get("pending")
            if pending and pending.get("status") == "PENDING":
                st.warning(f"Needs confirmation: {pending['type'].replace('_', ' ')}")
                st.json(pending["payload"])
                col_confirm, col_cancel = st.columns(2)
                with col_confirm:
                    confirm_label = "Confirm simulation" if DEMO_MODE else "Confirm and send via Sandbox"
                    if st.button(confirm_label, key=f"confirm-{pending['id']}", type="primary"):
                        result = api("POST", f"/actions/{pending['id']}/confirm")
                        if result:
                            entry["pending"]["status"] = "CONFIRMED"
                            st.success("Local demo invoice created." if DEMO_MODE else "PayPal Sandbox invoice sent.")
                            st.rerun()
                with col_cancel:
                    if st.button("Cancel", key=f"cancel-{pending['id']}"):
                        result = api("POST", f"/actions/{pending['id']}/cancel")
                        if result:
                            entry["pending"]["status"] = "CANCELLED"
                            st.info("Action cancelled. No invoice was created.")
                            st.rerun()
    prompt = st.chat_input("Describe an invoice or ask a question...")
    if prompt:
        st.session_state.messages.append({"role": "user", "content": prompt})
        result = api("POST", "/chat", json={"session_id": st.session_state.session_id, "message": prompt})
        if result:
            st.session_state.messages.append({"role": "assistant", "content": result["reply"], "pending": result.get("pending_action")})
        st.rerun()

with right:
    st.subheader("Overview")
    totals = api("GET", "/insights")
    if totals:
        cards = st.columns(3)
        cards[0].metric("Outstanding", f"${float(totals['outstanding']):,.2f}")
        cards[1].metric("Paid this month", f"${float(totals['paid_this_month']):,.2f}")
        cards[2].metric("Overdue", f"${float(totals['overdue']):,.2f}")
    invoices_response = api("GET", "/invoices")
    if invoices_response:
        invoices = invoices_response["invoices"]
        if invoices:
            rows = [{"Client": i["draft"]["client_name"], "Email": i["draft"]["client_email"], "Total": f"{i['draft']['currency']} {float(i['total']):,.2f}", "Status": i["status"], "Due": i["due_date"], "ID": i["id"]} for i in invoices]
            st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)
            st.caption("Fictional local invoices." if DEMO_MODE else "Invoices tracked locally; provider status refreshes from PayPal Sandbox.")
            selected = st.selectbox("Refresh simulated status", [i["id"] for i in invoices], format_func=lambda key: next(f"{i['draft']['client_name']} | {key}" for i in invoices if i["id"] == key))
            if st.button("Refresh", key="refresh-status"):
                result = api("POST", f"/invoices/{selected}/refresh")
                if result:
                    st.toast(f"Status: {result['status']}")
                    st.rerun()
        else:
            st.info("No invoices yet. Confirmed demo invoices will appear here.")

    st.divider()
    st.subheader("Reminder draft")
    st.text_area("Editable text", "Hello, this is a reminder that your invoice is approaching its due date. Please contact me if you have questions.", height=100)
    st.caption("This text stays local and is never sent." if DEMO_MODE else "Reminder actions require an explicit confirmation.")

st.caption("InvoicePilot | Local demo | Fictional data" if DEMO_MODE else "InvoicePilot | PayPal Sandbox | Explicit confirmation required")
