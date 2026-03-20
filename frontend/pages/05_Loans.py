import streamlit as st
import pandas as pd
from datetime import date
import calendar
import sys, os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from styles import load_css, fmt
from services_client import (
    get_active_loans,
    get_closed_loans,
    get_loan_detail,
    add_loan,
    update_loan,
    delete_loan,
    log_loan_payment,
    delete_loan_payment,
    get_loan_payments
)

st.set_page_config(
    page_title="Loans — CardSense",
    page_icon="🏦",
    layout="wide",
    initial_sidebar_state="expanded"
)

load_css()

LOAN_TYPES = ["Personal", "Home", "Car", "Education",
              "Gold", "Business", "Other"]


 
# HELPE

def fmt_date(d) -> str:
    if d is None:
        return '—'
    try:
        return pd.to_datetime(d).strftime('%d %b %Y')
    except:
        return str(d)


def compute_amortization(principal, annual_rate, tenure_months,
                          emi, start_date) -> list:
    schedule     = []
    balance      = principal
    monthly_rate = annual_rate / 12 / 100

    for month in range(1, tenure_months + 1):
        interest_comp  = round(balance * monthly_rate, 2)
        principal_comp = round(emi - interest_comp, 2)
        if principal_comp > balance:
            principal_comp = balance
            actual_emi     = principal_comp + interest_comp
        else:
            actual_emi = emi
        balance = max(round(balance - principal_comp, 2), 0)

        pay_month = start_date.month + month - 1
        pay_year  = start_date.year + (pay_month - 1) // 12
        pay_month = (pay_month - 1) % 12 + 1
        try:
            pay_date = date(pay_year, pay_month, start_date.day)
        except:
            last_day = calendar.monthrange(pay_year, pay_month)[1]
            pay_date = date(pay_year, pay_month, last_day)

        schedule.append({
            'month':     month,
            'date':      pay_date,
            'emi':       actual_emi,
            'principal': principal_comp,
            'interest':  interest_comp,
            'balance':   balance
        })
    return schedule



#SESSION STATE
 
if 'selected_loan_id' not in st.session_state:
    st.session_state['selected_loan_id'] = None
if 'show_add_loan' not in st.session_state:
    st.session_state['show_add_loan'] = False



# LOAN LIST
if st.session_state['selected_loan_id'] is None:

    col_title, col_add = st.columns([4, 1])
    with col_title:
        st.title("Loans")
        st.caption("Track EMIs, outstanding principal and repayment progress")
    with col_add:
        st.write("")
        if st.button("➕ Add Loan", type="primary",
                     use_container_width=True, key="toggle_add_loan"):
            st.session_state['show_add_loan'] = \
                not st.session_state['show_add_loan']

    #    Add Loan Form   
    if st.session_state['show_add_loan']:
        st.subheader("Add a New Loan")
        with st.form("add_loan_form", clear_on_submit=True):
            col1, col2 = st.columns(2)
            with col1:
                lender_name  = st.text_input("Lender Name",
                    placeholder="e.g. HDFC Bank, Bajaj Finance")
                loan_type    = st.selectbox("Loan Type", LOAN_TYPES)
                loan_nickname = st.text_input("Nickname (optional)",
                    placeholder="e.g. Home Loan, Bike Loan")
                principal_amount = st.number_input(
                    "Original Principal (₹)",
                    min_value=0.0, value=100000.0, step=1000.0)
                outstanding_principal = st.number_input(
                    "Current Outstanding (₹)",
                    min_value=0.0, value=100000.0, step=1000.0)
            with col2:
                interest_rate = st.number_input(
                    "Interest Rate (% p.a.)",
                    min_value=0.0, max_value=50.0, value=12.0, step=0.1)
                tenure_months = st.number_input(
                    "Total Tenure (months)",
                    min_value=1, max_value=360, value=24, step=1)
                emi_amount = st.number_input(
                    "EMI Amount (₹)",
                    min_value=0.0, value=5000.0, step=100.0)
                emi_date = st.number_input(
                    "EMI Due Date (day of month)",
                    min_value=1, max_value=31, value=5)
                start_date = st.date_input(
                    "Loan Start Date", value=date.today())
                notes = st.text_area(
                    "Notes (optional)",
                    placeholder="Loan account number, branch, etc.",
                    height=80)

            st.caption(
                "Current Outstanding = remaining principal today. "
                "If this is a new loan, it equals Original Principal."
            )

            if st.form_submit_button("Add Loan", type="primary",
                                     use_container_width=True):
                if not lender_name.strip():
                    st.error("Please enter a lender name")
                elif emi_amount <= 0:
                    st.error("Please enter a valid EMI amount")
                else:
                    payload = {
                        "lender_name":           lender_name.strip(),
                        "loan_type":             loan_type,
                        "loan_nickname":         loan_nickname.strip() or None,
                        "principal_amount":      float(principal_amount),
                        "outstanding_principal": float(outstanding_principal),
                        "interest_rate":         float(interest_rate),
                        "tenure_months":         int(tenure_months),
                        "emi_amount":            float(emi_amount),
                        "emi_date":              int(emi_date),
                        "start_date":            start_date.strftime("%Y-%m-%d"),
                        "notes":                 notes.strip() or None
                    }
                    try:
                        r = add_loan(payload)
                        if r.status_code == 200:
                            st.success("Loan added!")
                            st.session_state['show_add_loan'] = False
                            st.balloons()
                            st.rerun()
                        else:
                            st.error("Failed: " + str(r.json()))
                    except Exception as e:
                        st.error(str(e))
        st.divider()

    #    Fetch loans   
    loans_df  = get_active_loans()
    closed_df = get_closed_loans()

    if loans_df.empty and closed_df.empty:
        st.info("No loans added yet. Click **➕ Add Loan** above to start tracking.")

    else:
        #    Active loan summary   
        if not loans_df.empty:
            total_outstanding = loans_df['outstanding_principal'].astype(float).sum()
            total_emi         = loans_df['emi_amount'].astype(float).sum()

            c1, c2, c3 = st.columns(3)
            with c1:
                st.metric("Total Outstanding", fmt(total_outstanding))
            with c2:
                st.metric("Total Monthly EMI", fmt(total_emi))
            with c3:
                st.metric("Active Loans", str(len(loans_df)))

            st.divider()
            st.caption("ACTIVE LOANS")

            for _, loan in loans_df.iterrows():
                loan_id     = int(loan['id'])
                name        = (str(loan['loan_nickname']) if loan['loan_nickname']
                               else str(loan['lender_name']))
                lender      = str(loan['lender_name'])
                loan_type   = str(loan['loan_type'])
                emi_amount  = float(loan['emi_amount'])
                outstanding = float(loan['outstanding_principal'])
                total_paid  = float(loan['total_paid'])
                pct_paid    = float(loan['pct_paid'] or 0)
                months_rem  = int(float(loan['months_remaining'] or 0))
                days_emi    = int(float(loan['days_until_emi'] or 0))
                interest    = float(loan['interest_rate'])

                if days_emi == 0:
                    due_label = "🔴 EMI due today!"
                elif days_emi <= 3:
                    due_label = "🔴 EMI in " + str(days_emi) + "d"
                elif days_emi <= 7:
                    due_label = "🟡 EMI in " + str(days_emi) + "d"
                else:
                    due_label = "🟢 EMI in " + str(days_emi) + "d"

                col_a, col_b, col_c = st.columns([3, 2, 2])
                with col_a:
                    st.markdown(
                        "**" + name + "**  \n"
                        + lender + "  ·  `" + loan_type + "`  ·  "
                        + '{:.1f}%'.format(interest) + " p.a."
                    )
                with col_b:
                    st.metric("Outstanding", fmt(outstanding))
                with col_c:
                    st.metric("EMI", fmt(emi_amount),
                              str(months_rem) + " months left")

                st.progress(min(pct_paid / 100, 1.0))
                st.caption(
                    due_label + "  ·  "
                    + '{:.1f}%'.format(pct_paid) + " paid  ·  "
                    + "Total paid: " + fmt(total_paid)
                )

                col_view, col_pay = st.columns(2)
                with col_view:
                    if st.button("View Details",
                                 key="view_loan_" + str(loan_id),
                                 use_container_width=True):
                        st.session_state['selected_loan_id'] = loan_id
                        st.rerun()
                with col_pay:
                    if st.button("💳 Log EMI " + fmt(emi_amount),
                                 type="primary",
                                 key="pay_loan_" + str(loan_id),
                                 use_container_width=True):
                        st.session_state['quick_pay_loan_id'] = loan_id

                #    Quick pay form   
                if st.session_state.get('quick_pay_loan_id') == loan_id:
                    with st.form("qp_loan_" + str(loan_id)):
                        st.caption("Log EMI Payment")
                        col1, col2 = st.columns(2)
                        with col1:
                            pay_date = st.date_input("Payment Date",
                                value=date.today(), key="qpd_" + str(loan_id))
                            pay_amount = st.number_input("Amount Paid (₹)",
                                value=emi_amount, min_value=0.0, step=100.0,
                                key="qpa_" + str(loan_id))
                        with col2:
                            ref_num = st.text_input("Reference Number",
                                placeholder="Optional",
                                key="qpr_" + str(loan_id))
                            pay_notes = st.text_input("Notes",
                                placeholder="Optional",
                                key="qpn_" + str(loan_id))
                        if st.form_submit_button("Confirm Payment",
                                                 type="primary",
                                                 use_container_width=True):
                            payload = {
                                "loan_id":          loan_id,
                                "payment_date":     pay_date.strftime("%Y-%m-%d"),
                                "amount_paid":      float(pay_amount),
                                "reference_number": ref_num or None,
                                "notes":            pay_notes or None
                            }
                            try:
                                r = log_loan_payment(payload)
                                if r.status_code == 200:
                                    res = r.json()
                                    st.success(
                                        "EMI logged!  Principal: "
                                        + fmt(res['principal_component'])
                                        + "  ·  Interest: "
                                        + fmt(res['interest_component'])
                                    )
                                    st.session_state.pop('quick_pay_loan_id', None)
                                    st.rerun()
                                else:
                                    st.error("Failed: " + r.text)
                            except Exception as e:
                                st.error(str(e))

                st.divider()

        #    Closed loans   
        if not closed_df.empty:
            st.caption("CLOSED LOANS")
            for _, loan in closed_df.iterrows():
                loan_id  = int(loan['id'])
                name     = (str(loan['loan_nickname']) if loan['loan_nickname']
                            else str(loan['lender_name']))

                col_a, col_b, col_c = st.columns([3, 2, 2])
                with col_a:
                    st.markdown(
                        "**" + name + "**  ✅ Closed  \n"
                        + str(loan['lender_name']) + "  ·  "
                        + str(loan['loan_type'])
                    )
                with col_b:
                    st.metric("Total Paid", fmt(float(loan['total_paid'])))
                with col_c:
                    st.metric("Original", fmt(float(loan['principal_amount'])))

                st.progress(1.0)

                if st.button("View Details",
                             key="view_closed_" + str(loan_id)):
                    st.session_state['selected_loan_id'] = loan_id
                    st.rerun()

                st.divider()


# LOAN DETAIL
else:
    loan_id = st.session_state['selected_loan_id']

    if st.button("← Back to Loans", key="back_to_loans"):
        st.session_state['selected_loan_id'] = None
        st.rerun()

    loan_data = get_loan_detail(loan_id)
    if not loan_data:
        st.error("Loan not found")
        st.session_state['selected_loan_id'] = None
        st.rerun()
    loan_df = pd.DataFrame([loan_data])

    if loan_df.empty:
        st.error("Loan not found")
        st.session_state['selected_loan_id'] = None
        st.rerun()

    loan        = loan_df.iloc[0]
    name        = (str(loan['loan_nickname']) if loan['loan_nickname']
                   else str(loan['lender_name']))
    lender      = str(loan['lender_name'])
    loan_type   = str(loan['loan_type'])
    principal   = float(loan['principal_amount'])
    outstanding = float(loan['outstanding_principal'])
    total_paid  = float(loan['total_paid'])
    interest    = float(loan['interest_rate'])
    tenure      = int(loan['tenure_months'])
    emi_amount  = float(loan['emi_amount'])
    emi_date    = int(loan['emi_date'])
    status      = str(loan['status'])
    notes       = str(loan['notes'] or '')
    try:
        start_date = pd.to_datetime(loan['start_date']).date()
    except:
        start_date = date.today()

    pct_paid = (total_paid / principal * 100) if principal > 0 else 0
    months_elapsed   = max(0, (date.today().year - start_date.year) * 12
                            + date.today().month - start_date.month)
    months_remaining = max(0, tenure - months_elapsed)

    #    Detail header   
    st.title(name)
    st.caption(lender + "  ·  " + loan_type + " Loan  ·  " + status)

    c1, c2, c3, c4, c5, c6 = st.columns(6)
    with c1: st.metric("Principal",    fmt(principal))
    with c2: st.metric("Outstanding",  fmt(outstanding))
    with c3: st.metric("Total Paid",   fmt(total_paid))
    with c4: st.metric("EMI",          fmt(emi_amount))
    with c5: st.metric("Rate",         '{:.1f}%'.format(interest) + " p.a.")
    with c6: st.metric("Months Left",  str(months_remaining))

    st.progress(min(pct_paid / 100, 1.0))
    st.caption(
        "Paid {:.1f}%".format(pct_paid)
        + "  ·  Started " + fmt_date(start_date)
        + "  ·  EMI on " + str(emi_date) + "th every month"
        + ("  ·  " + notes if notes else "")
    )

    st.divider()

    #    Action buttons   
    col_e, col_d, col_pay = st.columns([1, 1, 2])
    with col_e:
        if st.button("✎ Edit", key="edit_loan_" + str(loan_id)):
            k = "edit_loan_open_" + str(loan_id)
            st.session_state[k] = not st.session_state.get(k, False)
    with col_d:
        if st.button("🗑 Delete", key="del_loan_" + str(loan_id)):
            st.session_state["confirm_del_loan"] = loan_id
    with col_pay:
        if st.button("💳 Log EMI Payment", type="primary",
                     key="detail_pay_loan_" + str(loan_id),
                     use_container_width=True):
            k = "detail_pay_open_" + str(loan_id)
            st.session_state[k] = not st.session_state.get(k, False)

    #    Edit form   
    if st.session_state.get("edit_loan_open_" + str(loan_id), False):
        with st.form("edit_loan_" + str(loan_id)):
            col1, col2 = st.columns(2)
            with col1:
                new_nick   = st.text_input("Nickname",
                    value=str(loan['loan_nickname'] or ''),
                    key="eln_" + str(loan_id))
                new_lender = st.text_input("Lender", value=lender,
                    key="ell_" + str(loan_id))
                new_emi    = st.number_input("EMI Amount (₹)",
                    value=emi_amount, key="ele_" + str(loan_id))
            with col2:
                new_rate    = st.number_input("Interest Rate (%)",
                    value=interest, key="elr_" + str(loan_id))
                new_emi_date = st.number_input("EMI Date",
                    value=emi_date, min_value=1, max_value=31,
                    key="eld_" + str(loan_id))
                new_outstanding = st.number_input("Outstanding Principal (₹)",
                    value=outstanding, key="elo_" + str(loan_id))
                new_status = st.selectbox("Status", ["Active", "Closed"],
                    index=0 if status == 'Active' else 1,
                    key="els_" + str(loan_id))
            new_notes = st.text_area("Notes", value=notes,
                key="eln2_" + str(loan_id))
            if st.form_submit_button("Save Changes", type="primary",
                                     use_container_width=True):
                try:
                    r = update_loan(loan_id,
                        json={
                            "loan_nickname":         new_nick or None,
                            "lender_name":           new_lender,
                            "emi_amount":            float(new_emi),
                            "interest_rate":         float(new_rate),
                            "emi_date":              int(new_emi_date),
                            "outstanding_principal": float(new_outstanding),
                            "status":                new_status,
                            "notes":                 new_notes or None
                        })
                    if r.status_code == 200:
                        st.success("Loan updated!")
                        st.session_state.pop(
                            "edit_loan_open_" + str(loan_id), None)
                        st.rerun()
                except Exception as e:
                    st.error(str(e))

    #    Log payment form   
    if st.session_state.get("detail_pay_open_" + str(loan_id), False):
        with st.form("detail_pay_loan_" + str(loan_id)):
            col1, col2 = st.columns(2)
            with col1:
                pay_date = st.date_input("Payment Date", value=date.today(),
                    key="dpd_" + str(loan_id))
                pay_amount = st.number_input("Amount Paid (₹)",
                    value=emi_amount, min_value=0.0, step=100.0,
                    key="dpa_" + str(loan_id))
            with col2:
                ref_num   = st.text_input("Reference Number",
                    placeholder="Optional", key="dpr_" + str(loan_id))
                pay_notes = st.text_input("Notes",
                    placeholder="Optional", key="dpn_" + str(loan_id))
            if st.form_submit_button("Confirm Payment", type="primary",
                                     use_container_width=True):
                payload = {
                    "loan_id":          loan_id,
                    "payment_date":     pay_date.strftime("%Y-%m-%d"),
                    "amount_paid":      float(pay_amount),
                    "reference_number": ref_num or None,
                    "notes":            pay_notes or None
                }
                try:
                    r = log_loan_payment(payload)
                    if r.status_code == 200:
                        res = r.json()
                        st.success(
                            "Payment logged!  Principal: "
                            + fmt(res['principal_component'])
                            + "  ·  Interest: "
                            + fmt(res['interest_component'])
                        )
                        st.session_state.pop(
                            "detail_pay_open_" + str(loan_id), None)
                        st.rerun()
                    else:
                        st.error("Failed: " + r.text)
                except Exception as e:
                    st.error(str(e))

    #    Confirm delete   
    if st.session_state.get("confirm_del_loan") == loan_id:
        st.warning("Delete **" + name + "**? All payment history will be "
                   "deleted too. This cannot be undone.")
        col_y, col_n = st.columns(2)
        with col_y:
            if st.button("Yes, Delete", key="cdl_" + str(loan_id),
                         use_container_width=True):
                try:
                    r = delete_loan(loan_id)
                    if r.status_code == 200:
                        st.success("Loan deleted")
                        st.session_state.pop("confirm_del_loan", None)
                        st.session_state['selected_loan_id'] = None
                        st.rerun()
                except Exception as e:
                    st.error(str(e))
        with col_n:
            if st.button("Cancel", key="cdln_" + str(loan_id),
                         use_container_width=True):
                st.session_state.pop("confirm_del_loan", None)
                st.rerun()

    st.divider()

  
    # PAYMENT HISTORY

    st.subheader("Payment History")

    payments = get_loan_payments(loan_id)

    if not payments:
        st.info("No payments logged yet.")
    else:
        for pay in payments:
            try:
                pd_str = pd.to_datetime(pay['payment_date']).strftime('%d %b %Y')
            except:
                pd_str = str(pay['payment_date'])

            principal_c = float(pay.get('principal_component') or 0)
            interest_c  = float(pay.get('interest_component') or 0)
            ref         = str(pay.get('reference_number') or '')

            col_a, col_b = st.columns([4, 1])
            with col_a:
                st.markdown(
                    "**" + pd_str + "**  ·  "
                    + "Principal: " + fmt(principal_c)
                    + "  ·  Interest: " + fmt(interest_c)
                    + ("  ·  Ref: " + ref if ref else "")
                )
            with col_b:
                st.metric("", fmt(float(pay['amount_paid'])))

        st.divider()

        with st.expander("🗑 Delete a Payment"):
            pay_options = {
                pd.to_datetime(p['payment_date']).strftime('%d %b %Y')
                + ' — ' + fmt(p['amount_paid']): p['id']
                for p in payments
            }
            selected_pay = st.selectbox("Select payment to delete",
                list(pay_options.keys()),
                key="del_pay_select_" + str(loan_id))
            if st.button("Delete Selected Payment",
                         key="del_pay_btn_" + str(loan_id),
                         use_container_width=True):
                pay_id_to_del = pay_options[selected_pay]
                try:
                    r = delete_loan_payment(pay_id_to_del)
                    if r.status_code == 200:
                        st.success("Payment deleted!")
                        st.rerun()
                    else:
                        st.error("Failed: " + r.text)
                except Exception as e:
                    st.error(str(e))

    st.divider()

    # AMORTIZATION SCHEDULE

    st.subheader("Amortization Schedule")

    schedule = compute_amortization(
        principal, interest, tenure, emi_amount, start_date
    )

    # Building dataframe 
    rows = []
    for row in schedule:
        is_past    = row['date'] < date.today()
        is_current = (row['date'].year == date.today().year
                      and row['date'].month == date.today().month)
        rows.append({
            'Month':     row['month'],
            'Date':      row['date'].strftime('%b %Y'),
            'EMI':       fmt(row['emi']),
            'Principal': fmt(row['principal']),
            'Interest':  fmt(row['interest']),
            'Balance':   fmt(row['balance']),
            '_current':  is_current,
            '_past':     is_past
        })

    amort_df = pd.DataFrame(rows)

    # Show current month callout
    current_rows = amort_df[amort_df['_current']]
    if not current_rows.empty:
        cr = current_rows.iloc[0]
        c1, c2, c3 = st.columns(3)
        with c1: st.metric("This Month — EMI",       cr['EMI'])
        with c2: st.metric("Principal Component",    cr['Principal'])
        with c3: st.metric("Interest Component",     cr['Interest'])

    st.dataframe(
        amort_df.drop(columns=['_current', '_past']),
        use_container_width=True,
        hide_index=True
    )

    total_interest_paid = sum(r['interest'] for r in schedule)
    c1, c2, c3 = st.columns(3)
    with c1: st.metric("Total Payable",  fmt(emi_amount * tenure))
    with c2: st.metric("Total Interest", fmt(total_interest_paid))
    with c3: st.metric("Principal",      fmt(principal))