import streamlit as st
import sys, os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from services_client import (
    get_dashboard_summary,
    get_all_cards_summary,
    get_due_soon_alerts,
    refresh_analytics
)

st.set_page_config(
    page_title="Dashboard — CardSense",
    page_icon="🏠",
    layout="wide"
)
st.title("🏠 Dashboard")

#   Refresh button  
col_refresh, col_empty = st.columns([1, 4])
with col_refresh:
    if st.button("🔄 Refresh Data", type="primary"):
        with st.spinner("Rebuilding analytics models..."):
            result = refresh_analytics()
        if result.get("success"):
            st.cache_data.clear()
            st.success("✅ Data refreshed successfully!")
            st.rerun()
        else:
            st.error("dbt error: " + result.get("message", "Unknown error"))

#   Summary Metrics  
summary = get_dashboard_summary()

if summary:
    col1, col2, col3, col4 = st.columns(4)

    with col1:
        st.metric(
            label="💰 Total Outstanding",
            value="₹{:,.2f}".format(summary['total_outstanding']),
            delta=str(summary['total_statements']) + " statements"
        )
    with col2:
        st.metric(
            label="✅ Paid This Cycle",
            value="₹{:,.2f}".format(summary['total_paid']),
            delta=str(summary['paid_count']) + " cards cleared"
        )
    with col3:
        st.metric(
            label="⚠️ Due Soon",
            value=str(summary['due_soon_count']) + " cards",
            delta="Within 7 days",
            delta_color="inverse"
        )
    with col4:
        st.metric(
            label="🚨 Overdue",
            value=str(summary['overdue_count']) + " cards",
            delta_color="inverse"
        )

st.markdown("---")

#   Danger Zone  
alerts = get_due_soon_alerts()

if not alerts.empty:
    st.subheader("🚨 Danger Zone — Due in 7 Days")
    for _, row in alerts.iterrows():
        days  = int(row['days_until_due'])
        color = "🔴" if days <= 3 else "🟡"

        c1, c2, c3, c4 = st.columns([3, 2, 2, 1])
        with c1:
            st.markdown("**" + color + " " + str(row['card_display_name']) + "**")
            st.caption(str(row['masked_card_number']))
        with c2:
            st.markdown("**₹{:,.2f}**".format(float(row['outstanding'])))
            st.caption("Outstanding")
        with c3:
            try:
                import pandas as pd
                due_str = pd.to_datetime(row['due_date']).strftime('%d %b %Y')
            except Exception:
                due_str = str(row['due_date'])
            st.markdown("**" + due_str + "**")
            st.caption(str(days) + " days left")
        with c4:
            st.markdown("`" + str(row['status']) + "`")
        st.divider()
else:
    st.success("✅ No payments due in the next 7 days!")

st.markdown("---")

#   All Cards Overview  
st.subheader("💳 All Cards — Current Status")
cards = get_all_cards_summary()

if not cards.empty:
    for _, row in cards.iterrows():
        with st.expander(
            ("✅" if row['status'] == 'Paid'
             else "🚫" if row['is_overdue']
             else "❌")
            + " " + str(row['card_display_name'])
            + " — ₹{:,.2f} due — ".format(float(row['outstanding']))
            + ("Overdue" if row['is_overdue'] else str(row['status']))
        ):
            c1, c2, c3 = st.columns(3)
            with c1:
                st.metric("Statement Amount",
                          "₹{:,.2f}".format(float(row['total_amount'])))
                st.metric("Minimum Due",
                          "₹{:,.2f}".format(float(row['minimum_due'])))
            with c2:
                st.metric("Amount Paid",
                          "₹{:,.2f}".format(float(row['total_paid'])))
                st.metric("Outstanding",
                          "₹{:,.2f}".format(float(row['outstanding'])))
            with c3:
                st.metric("Due Date", str(row['due_date']))
                st.metric("Days Until Due", str(row['days_until_due']))

            progress = float(row['payment_progress_pct']) / 100
            st.progress(
                min(progress, 1.0),
                text="Payment Progress: " + str(row['payment_progress_pct']) + "%"
            )

            if row['billing_period_display']:
                st.caption("📅 Billing Period: " + str(row['billing_period_display']))

            if row['pdf_link']:
                st.link_button("📄 View Statement PDF", str(row['pdf_link']))

            col_a, col_b = st.columns(2)
            with col_a:
                if st.button("💸 Log Payment",
                             key="pay_" + str(row['statement_id'])):
                    st.switch_page("pages/03_Payments.py")
            with col_b:
                if st.button("🔍 View Transactions",
                             key="txn_" + str(row['statement_id'])):
                    st.session_state['selected_statement_id'] = \
                        int(row['statement_id'])
                    st.switch_page("pages/02_Statements.py")
else:
    st.info("No statements found. Upload a PDF statement to get started!")
    if st.button("📤 Upload Statement"):
        st.switch_page("pages/02_Statements.py")