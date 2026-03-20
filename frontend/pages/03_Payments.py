import streamlit as st
import pandas as pd
import sys, os
from datetime import date
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from services_client import (
    get_unpaid_statements,
    get_payment_history,
    get_statement_reconciliation,
    log_payment
)

st.set_page_config(
    page_title="Payments — CardSense",
    page_icon="💸",
    layout="wide"
)
st.title("💸 Payments")

#  Log New Payment
st.subheader("➕ Log a Payment")

col1, col2 = st.columns([1, 1])

with col1:
    with st.form("payment_form", clear_on_submit=True):

        stmts = get_unpaid_statements()

        if not stmts.empty:
            stmt_options = {
                str(row['display_name']): int(row['statement_id'])
                for _, row in stmts.iterrows()
            }
            selected_label = st.selectbox(
                "Select Statement",
                list(stmt_options.keys())
            )
            selected_stmt = stmt_options[selected_label]

            selected_row = stmts[
                stmts['statement_id'] == selected_stmt
            ].iloc[0]
            outstanding = float(selected_row['outstanding'])
            card_id     = int(selected_row['card_id'])

            st.caption("Outstanding amount: ₹{:,.2f}".format(outstanding))
        else:
            st.info("All statements are paid! 🎉")
            selected_stmt = None
            card_id       = None
            outstanding   = 0.0

        payment_type = st.radio(
            "Payment Type",
            ["Full", "Partial", "Advance"],
            horizontal=True
        )

        default_amount = outstanding if payment_type == "Full" else 0.0

        amount = st.number_input(
            "Amount (₹)",
            min_value=0.0,
            value=default_amount,
            step=100.0,
            format="%.2f"
        )

        payment_date = st.date_input("Payment Date", value=date.today())
        reference    = st. _input(
            "UTR / Reference Number", placeholder="Optional"
        )
        notes        = st. _input(
            "Notes", placeholder="e.g. Paid via PhonePe"
        )

        submitted = st.form_submit_button(
            "✅ Record Payment", type="primary",
            use_container_width=True
        )

        if submitted and selected_stmt:
            result = log_payment({
                "card_id":          card_id,
                "statement_id":     selected_stmt,
                "payment_date":     str(payment_date),
                "amount":           amount,
                "payment_type":     payment_type,
                "reference_number": reference,
                "notes":            notes
            })
            if "error" not in result and result.get("id"):
                st.success(
                    "✅ Payment of ₹{:,.2f} recorded successfully!".format(amount)
                )
                st.rerun()
            else:
                st.error("Error: " + str(result))

with col2:
    if selected_stmt:
        st.markdown("**📊 Statement Reconciliation**")
        recon = get_statement_reconciliation(selected_stmt)

        if recon:
            st.metric("Opening Balance",
                      "₹{:,.2f}".format(float(recon['opening_balance'])))
            st.metric("Charges This Period",
                      "₹{:,.2f}".format(float(recon['charges_this_period'])))
            st.metric("Payments Received",
                      "₹{:,.2f}".format(float(recon['payments_received'])))
            st.metric("Closing Balance",
                      "₹{:,.2f}".format(float(recon['closing_balance'])))

            if recon.get('interest_risk'):
                st.warning(
                    "⚠️ Interest Risk! Estimated monthly interest: "
                    "₹{:,.2f}".format(float(recon['estimated_interest']))
                )

st.markdown("---")

#  Payment History
st.subheader("📜 Payment History")

payments = get_payment_history()

if not payments.empty:
    col1, col2, col3 = st.columns(3)
    col1.metric("Total Payments", len(payments))
    col2.metric("Total Paid",
                "₹{:,.2f}".format(float(payments['payment_amount'].sum())))

    this_month = pd.Timestamp.now().strftime('%b %Y')
    this_month_total = payments[
        payments['payment_month'] == this_month
    ]['payment_amount'].sum()
    col3.metric("This Month", "₹{:,.2f}".format(float(this_month_total)))

    display = payments.copy()
    display['payment_amount'] = display['payment_amount'].apply(
        lambda x: "₹{:,.2f}".format(float(x))
    )
    display.columns = ['Date', 'Card', 'Amount',
                       'Type', 'Reference', 'Notes', 'Month']
    st.dataframe(display, use_container_width=True, hide_index=True)
else:
    st.info("No payments recorded yet.")