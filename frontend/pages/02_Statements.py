import streamlit as st
import sys, os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from services_client import (
    get_active_cards,
    get_all_cards_summary,
    get_transactions_for_statement,
    upload_statement_pdf,
    update_pdf_link
)

st.set_page_config(
    page_title="Statements — CardSense",
    page_icon="📄",
    layout="wide"
)
st.title("📄 Statements & Transactions")

#   Upload New Statement  
with st.expander("📤 Upload New Statement PDF", expanded=False):
    st.markdown(
        "Upload your bank statement PDF and let "
        "Gemini AI extract all transactions automatically."
    )

    cards_df = get_active_cards()

    if not cards_df.empty:
        col1, col2 = st.columns(2)
        with col1:
            card_options = {
                str(row['bank_name']) + " " + str(row['card_nickname']): int(row['id'])
                for _, row in cards_df.iterrows()
            }
            selected_label = st.selectbox(
                "Select Card",
                list(card_options.keys())
            )
            selected_card = card_options[selected_label]
            bank_name     = selected_label.split()[0]

        with col2:
            pdf_password = st.text_input(
                "PDF Password (if protected)",
                type="password",
                placeholder="e.g. your DOB: 01011990"
            )

        uploaded_file = st.file_uploader("Choose PDF file", type="pdf")

        if uploaded_file and st.button(
            "🚀 Parse with Gemini AI", type="primary"
        ):
            with st.spinner(
                "Extracting text and parsing with Gemini AI... "
                "This may take 10-15 seconds"
            ):
                result = upload_statement_pdf(
                    card_id=selected_card,
                    bank_name=bank_name,
                    pdf_password=pdf_password,
                    file_bytes=uploaded_file.getvalue(),
                    filename=uploaded_file.name
                )

            if "error" not in result and result.get("transactions_extracted"):
                st.success(
                    "✅ Successfully extracted "
                    + str(result['transactions_extracted'])
                    + " transactions!"
                )
                st.rerun()
            else:
                st.error(
                    "Error: " + str(result.get("detail", result.get("error", "Unknown error")))
                )
    else:
        st.warning("No cards found. Please add cards first in Settings.")

st.markdown("---")

#   Statement List with Transactions  
st.subheader("📋 All Statements")

cards_summary = get_all_cards_summary()

if cards_summary.empty:
    st.info("No statements yet. Upload a PDF above to get started!")
else:
    col1, col2 = st.columns(2)
    with col1:
        bank_filter = st.selectbox(
            "Filter by Bank",
            ["All Banks"] + cards_summary['bank_name'].unique().tolist()
        )
    with col2:
        status_filter = st.selectbox(
            "Filter by Status",
            ["All", "Unpaid", "Partial", "Paid"]
        )

    filtered = cards_summary.copy()
    if bank_filter != "All Banks":
        filtered = filtered[filtered['bank_name'] == bank_filter]
    if status_filter != "All":
        filtered = filtered[filtered['status'] == status_filter]

    selected_stmt_id = st.session_state.get('selected_statement_id', None)

    for _, stmt in filtered.iterrows():
        is_expanded = (selected_stmt_id == stmt['statement_id'])

        status_emoji = (
            "✅" if stmt['status'] == 'Paid'
            else "🔴" if stmt['is_overdue']
            else "🟡" if stmt['is_due_soon']
            else "💳"
        )

        with st.expander(
            status_emoji + " "
            + str(stmt['card_display_name']) + " | "
            + str(stmt['statement_month']) + " | "
            + "₹{:,.2f}".format(float(stmt['total_amount'])) + " | "
            + str(stmt['status']),
            expanded=is_expanded
        ):
            col1, col2, col3, col4 = st.columns(4)
            with col1:
                st.metric("Total Due",
                          "₹{:,.2f}".format(float(stmt['total_amount'])))
            with col2:
                st.metric("Outstanding",
                          "₹{:,.2f}".format(float(stmt['outstanding'])))
            with col3:
                st.metric("Due Date", str(stmt['due_date']))
            with col4:
                st.metric("Days Left", str(stmt['days_until_due']))

            if stmt['billing_period_display']:
                st.caption("📅 " + str(stmt['billing_period_display']))

            if stmt['pdf_link']:
                st.link_button("📄 View Original PDF", str(stmt['pdf_link']))

            new_pdf_link = st.text_input(
                "Add/Update PDF Link (Google Drive)",
                value=stmt['pdf_link'] or "",
                key="pdf_link_" + str(stmt['statement_id']),
                placeholder="Paste Google Drive link here"
            )
            if st.button("💾 Save PDF Link",
                         key="save_pdf_" + str(stmt['statement_id'])):
                result = update_pdf_link(
                    int(stmt['statement_id']), new_pdf_link
                )
                if "error" not in result:
                    st.success("PDF link saved!")
                    st.rerun()
                else:
                    st.error(str(result.get("error")))

            st.markdown("---")
            st.markdown("**🔍 Transactions**")

            txns = get_transactions_for_statement(int(stmt['statement_id']))

            if not txns.empty:
                debits  = txns[txns['transaction_type'] == 'debit']['amount'].sum()
                credits = txns[txns['transaction_type'] == 'credit']['amount'].sum()

                t1, t2, t3 = st.columns(3)
                t1.metric("Total Transactions", len(txns))
                t2.metric("Total Debits",  "₹{:,.2f}".format(float(debits)))
                t3.metric("Total Credits", "₹{:,.2f}".format(float(credits)))

                search = st.text_input(
                    "🔍 Search transactions",
                    key="search_" + str(stmt['statement_id']),
                    placeholder="Search by merchant or category..."
                )
                if search:
                    txns = txns[
                        txns['merchant'].str.contains(
                            search, case=False, na=False
                        ) |
                        txns['category'].str.contains(
                            search, case=False, na=False
                        )
                    ]

                display_df = txns[[
                    'transaction_date', 'transaction_time',
                    'merchant', 'amount', 'transaction_type',
                    'category', 'is_emi', 'is_subscription'
                ]].copy()
                display_df.columns = [
                    'Date', 'Time', 'Merchant',
                    'Amount (₹)', 'Type', 'Category',
                    'EMI', 'Subscription'
                ]
                display_df['Amount (₹)'] = display_df['Amount (₹)'].apply(
                    lambda x: "₹{:,.2f}".format(float(x))
                )
                st.dataframe(
                    display_df,
                    use_container_width=True,
                    hide_index=True
                )
            else:
                st.info("No transactions found for this statement.")