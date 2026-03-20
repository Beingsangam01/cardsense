import streamlit as st
import sys, os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from services_client import (
    get_all_cards,
    add_card,
    update_card_password,
    deactivate_card,
    get_scheduler_status,
    enable_scheduler,
    disable_scheduler,
    run_import_now
)

st.set_page_config(page_title="Settings — CardSense", page_icon="⚙️", layout="wide")
st.title("⚙️ Settings")

  
# SCHEDULER CONTROL
 
st.subheader("🤖 Automation Scheduler")

# Get current scheduler status
try:
    status   = get_scheduler_status()
    is_enabled = status.get('enabled', False)
    last_run = status.get('last_run', 'Never')
    next_run = status.get('next_run', 'Not scheduled')
except:
    is_enabled = False
    last_run = "Unknown"
    next_run = "Unknown"

# Status display
col1, col2, col3 = st.columns(3)
with col1:
    if is_enabled:
        st.success("🟢 Scheduler is ON")
    else:
        st.error("🔴 Scheduler is OFF")
with col2:
    st.metric("Last Run", last_run)
with col3:
    st.metric("Next Scheduled Run", next_run)

st.caption("When ON: automatically imports statements at 9 AM and sends reminders at 8 AM daily")

# Toggle buttons
col_on, col_off, col_run = st.columns(3)

with col_on:
    if st.button(
        "✅ Enable Scheduler",
        type="primary" if not is_enabled else "secondary",
        use_container_width=True,
        disabled=is_enabled
    ):
        try:
            enable_scheduler()
            st.success("Scheduler enabled!")
            st.rerun()
        except Exception as e:
            st.error(str(e))

with col_off:
    if st.button(
        "⏸️ Disable Scheduler",
        type="primary" if is_enabled else "secondary",
        use_container_width=True,
        disabled=not is_enabled
    ):
        try:
            disable_scheduler()
            st.warning("Scheduler disabled")
            st.rerun()
        except Exception as e:
            st.error(str(e))

with col_run:
    if st.button(
        "▶️ Run Import Now",
        use_container_width=True,
        help="Manually trigger statement import regardless of scheduler state"
    ):
        try:
            run_import_now()
            st.info("Import started in background! Check FastAPI terminal for progress.")
        except Exception as e:
            st.error(str(e))

st.markdown("---")

 
# ADD NEW CARD

st.subheader("➕ Add New Card")

with st.form("add_card_form", clear_on_submit=True):
    col1, col2 = st.columns(2)

    with col1:
        bank_name = st.selectbox(
            "Bank",
            ["HDFC", "SBI", "ICICI", "Axis", "IndusInd",
             "Jupiter", "CSB", "Roar", "Other"]
        )
        card_nickname = st.text_input("Card Nickname", placeholder="e.g. Regalia Gold")
        last_four = st.text_input("Last 4 Digits", max_chars=4, placeholder="4821")
        email_sender = st.text_input(
            "Bank Statement Email Sender",
            placeholder="credit_cards@hdfcbank.net"
        )

    with col2:
        statement_day = st.number_input("Statement Day", min_value=1, max_value=31, value=10)
        due_day = st.number_input("Due Day", min_value=1, max_value=31, value=2)
        credit_limit = st.number_input("Credit Limit (₹)", min_value=0, value=100000, step=5000)
        pdf_password = st.text_input(
            "PDF Password",
            type="password",
            placeholder="Usually your DOB: 01011990"
        )

    if st.form_submit_button("💾 Add Card", type="primary", use_container_width=True):
        payload = {
            "bank_name": bank_name,
            "card_nickname": card_nickname,
            "last_four_digits": last_four,
            "statement_day": statement_day,
            "due_day": due_day,
            "credit_limit": credit_limit,
            "email_sender": email_sender,
            "pdf_password": pdf_password
        }
        try:
            response = add_card(payload)
            if response.status_code == 200:
                st.success(f"✅ {bank_name} {card_nickname} added!")
                st.rerun()
            else:
                st.error(f"Error: {response.json()}")
        except Exception as e:
            st.error(str(e))

st.markdown("---")

# EXISTING CARDS WITH PDF PASSWORD UPDATE
st.subheader("💳 Your Cards")

cards = get_all_cards()

if not cards.empty:
    for _, card in cards.iterrows():
        with st.expander(
            f"{'✅' if card['is_active'] == 'yes' else '❌'} "
            f"{card['bank_name']} {card['card_nickname']} •••• {card['last_four_digits']}"
        ):
            col1, col2 = st.columns(2)
            with col1:
                st.markdown(f"**Bank:** {card['bank_name']}")
                st.markdown(f"**Statement Day:** {card['statement_day']}th")
                st.markdown(f"**Due Day:** {card['due_day']}th")
                st.markdown(f"**Credit Limit:** ₹{card['credit_limit']:,}")

            with col2:
                st.markdown(f"**Email Sender:** `{card['email_sender'] or 'Not set'}`")
                pwd_status = "✅ Set" if card['pdf_password'] else "❌ Not set"
                st.markdown(f"**PDF Password:** {pwd_status}")

            # Update PDF password
            new_password = st.text_input(
                "Update PDF Password",
                type="password",
                key=f"pwd_{card['id']}",
                placeholder="Enter new password"
            )
            if st.button("💾 Update Password", key=f"save_pwd_{card['id']}"):
                try:
                    response = update_card_password(int(card['id']), new_password)
                    if response.status_code == 200:
                        st.success("Password updated!")
                    else:
                        st.error("Update failed")
                except Exception as e:
                    st.error(str(e))

            # Deactivate card
            if card['is_active'] == 'yes':
                if st.button("🗑️ Deactivate Card", key=f"del_{card['id']}"):
                    try:
                        deactivate_card(int(card['id']))
                        st.rerun()
                    except Exception as e:
                        st.error(str(e))
else:
    st.info("No cards added yet.")

st.markdown("---")
st.caption("CardSense v1.0 | FastAPI + dbt + Streamlit + Supabase + Gemini AI")