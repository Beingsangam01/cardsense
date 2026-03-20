import streamlit as st
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import pandas as pd
from datetime import date, timedelta
import sys, os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from styles import fmt, CHART_COLORS
from services_client import (
    get_spend_trends,
    get_spend_by_category,
    get_merchant_analysis,
    get_payment_reconciliation,
    get_all_loan_payments,
    get_shared_groups,
    get_active_loans,
    get_ai_insights,
    get_all_cards_summary
)

st.set_page_config(
    page_title="Insights - CardSense",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded"
)

CAT_COLORS = {
    "Food":          "#FF9500",
    "Travel":        "#0EA5E9",
    "Shopping":      "#EC4899",
    "Fuel":          "#64748B",
    "Entertainment": "#8B5CF6",
    "Healthcare":    "#00C853",
    "EMI":           "#FF3B30",
    "Subscription":  "#6C63FF",
    "Utilities":     "#14B8A6",
    "Transfer":      "#F59E0B",
    "Cashback":      "#00C853",
    "Other":         "#9CA3AF"
}


# PAGE HEADER + PERIOD FILTER
st.title("Insights")
st.caption("Data-driven analysis of your spending, payments and loans")

period = st.selectbox(
    "Time Period",
    ["All Time", "Last 12 Months", "Last 6 Months", "Last 3 Months"],
    index=0,
    key="ins_period"
)

today = date.today()
if period == "Last 3 Months":
    start_filter = today - timedelta(days=90)
elif period == "Last 6 Months":
    start_filter = today - timedelta(days=180)
elif period == "Last 12 Months":
    start_filter = today - timedelta(days=365)
else:
    start_filter = date(2000, 1, 1)

date_filter = "'" + start_filter.strftime('%Y-%m-%d') + "'"



# LOAD DATA FROM DBT MART TABLES
 
with st.spinner("Loading analytics..."):

    # Section 1 + 3: spend_trends mart
    spend_trends_df = get_spend_trends()

    # Section 2: spend_by_category mart
    spend_by_cat_df = get_spend_by_category()

    # Section 4: merchant_analysis mart
    merchant_df = get_merchant_analysis()

    # Section 5: payment_reconciliation mart
    pay_recon_df = get_payment_reconciliation()

    # Section 6: monthly_card_summary 
    shared_groups = get_shared_groups()

    # Section 7: monthly_card_summary data
    monthly_summary_df = get_all_cards_summary()

    # Section 8: loans 
    loan_df     = get_active_loans()
    loan_pay_df = pd.DataFrame()  

    # Fetch loan payments for active loans
    loan_pay_df = get_all_loan_payments()
    if not loan_pay_df.empty:
        loan_pay_df['month_key']   = pd.to_datetime(
            loan_pay_df['payment_date']
        ).dt.strftime('%Y-%m')
        loan_pay_df['month_label'] = pd.to_datetime(
            loan_pay_df['payment_date']
        ).dt.strftime('%b %Y')


# Existence checks 
has_trends   = not spend_trends_df.empty
has_cat      = not spend_by_cat_df.empty
has_merchant = not merchant_df.empty
has_recon    = not pay_recon_df.empty
has_summary  = not monthly_summary_df.empty
has_loans    = not loan_df.empty

if not has_trends and not has_cat:
    st.info("No data found for the selected period. Upload statements and run dbt to see insights.")
    st.stop()

# Type casting
if has_trends:
    spend_trends_df['total_spend']    = spend_trends_df['total_spend'].astype(float)
    spend_trends_df['rolling_3m_avg'] = spend_trends_df['rolling_3m_avg'].astype(float)
    spend_trends_df['month_start']    = pd.to_datetime(spend_trends_df['month_start'])

if has_cat:
    spend_by_cat_df['total_spend'] = spend_by_cat_df['total_spend'].astype(float)

if has_merchant:
    merchant_df['total_spend'] = merchant_df['total_spend'].astype(float)
    merchant_df['avg_spend']   = merchant_df['avg_spend'].astype(float)

if has_recon:
    pay_recon_df['charges_this_period'] = pay_recon_df['charges_this_period'].astype(float)
    pay_recon_df['payments_received']   = pay_recon_df['payments_received'].astype(float)
    pay_recon_df['closing_balance']     = pay_recon_df['closing_balance'].astype(float)
    pay_recon_df['estimated_interest']  = pay_recon_df['estimated_interest'].astype(float)

if has_summary:
    monthly_summary_df['outstanding']    = monthly_summary_df['outstanding'].astype(float)
    monthly_summary_df['utilization_pct'] = monthly_summary_df['utilization_pct'].astype(float)
    monthly_summary_df['credit_limit']   = monthly_summary_df['credit_limit'].astype(float)


 
# SECTION 1 - SPEND OVERVIEW

st.divider()
st.subheader("1 · Spend Overview")

if has_trends:
    total_spend    = spend_trends_df['total_spend'].sum()
    total_txns     = int(spend_trends_df['transaction_count'].sum())
    months_count   = spend_trends_df['transaction_month'].nunique()
    avg_monthly    = total_spend / max(months_count, 1)
    total_emi      = spend_trends_df['emi_spend'].astype(float).sum()
    total_subs     = spend_trends_df['subscription_spend'].astype(float).sum()

    # Biggest month across all cards combined
    monthly_agg = spend_trends_df.groupby(
        'transaction_month'
    )['total_spend'].sum()
    biggest_month     = monthly_agg.idxmax()
    biggest_month_amt = monthly_agg.max()

    # Anomaly count 
    anomaly_count = int(spend_trends_df['is_anomaly'].sum())

    c1, c2, c3, c4 = st.columns(4)
    with c1:
        st.metric("Total Spend", fmt(total_spend),
                  str(total_txns) + " transactions")
    with c2:
        st.metric("Avg Monthly", fmt(avg_monthly),
                  "Over " + str(months_count) + " month"
                  + ("s" if months_count != 1 else ""))
    with c3:
        st.metric("Biggest Month", fmt(biggest_month_amt), biggest_month)
    with c4:
        st.metric("EMI + Subscriptions",
                  fmt(total_emi + total_subs),
                  "Fixed monthly commitments")

    if anomaly_count > 0:
        st.warning(
            "⚠️ Flagged **" + str(anomaly_count)
            + " month(s)** as spend anomalies - unusually high spend "
            "detected compared to your rolling 3-month average."
        )

    col_l, col_r = st.columns(2)

    with col_l:
        # Spend by bank 
        bank_spend = spend_trends_df.groupby(
            'bank_name'
        )['total_spend'].sum().sort_values(ascending=False).reset_index()
        bank_spend.columns = ['Bank', 'Spend']

        fig = px.bar(bank_spend, x='Bank', y='Spend',
                     color='Bank',
                     color_discrete_sequence=CHART_COLORS,
                     title='Spend by Bank',
                     text=bank_spend['Spend'].apply(fmt))
        fig.update_traces(textposition='outside', marker_line_width=0)
        fig.update_layout(showlegend=False, height=320)
        st.plotly_chart(fig, use_container_width=True)

    with col_r:

        regular_spend = max(total_spend - total_emi - total_subs, 0)
        breakdown = pd.DataFrame({
            'Type':   ['Regular Spend', 'EMI', 'Subscriptions'],
            'Amount': [regular_spend, total_emi, total_subs]
        })
        breakdown = breakdown[breakdown['Amount'] > 0]

        fig2 = px.pie(breakdown, names='Type', values='Amount',
                      hole=0.5,
                      color='Type',
                      color_discrete_map={
                          'Regular Spend': '#6C63FF',
                          'EMI':           '#FF3B30',
                          'Subscriptions': '#0EA5E9'
                      },
                      title='Spend Composition')
        fig2.update_traces(textinfo='label+percent', textfont_size=10)
        fig2.update_layout(height=320)
        st.plotly_chart(fig2, use_container_width=True)


# SECTION 2 - CATEGORY ANALYSIS

st.divider()
st.subheader("2 · Category Analysis")

if has_cat:

    cat_summary = spend_by_cat_df.groupby('category').agg(
        total=('total_spend', 'sum'),
        count=('transaction_count', 'sum'),
        avg=('avg_transaction', 'mean'),
        max_txn=('max_transaction', 'max')
    ).reset_index().sort_values('total', ascending=False)
    cat_summary['pct'] = cat_summary['total'] / cat_summary['total'].sum() * 100

    col_l, col_r = st.columns(2)

    with col_l:
        fig = px.pie(cat_summary, names='category', values='total',
                     hole=0.5, color='category',
                     color_discrete_map=CAT_COLORS,
                     title='Spend Share by Category')
        fig.update_traces(textinfo='label+percent', textfont_size=10)
        fig.update_layout(height=360)
        st.plotly_chart(fig, use_container_width=True)

    with col_r:
        display_df = cat_summary[['category', 'total', 'count', 'avg', 'pct']].copy()
        display_df['total'] = display_df['total'].apply(fmt)
        display_df['avg']   = display_df['avg'].apply(fmt)
        display_df['pct']   = display_df['pct'].apply(lambda x: '{:.1f}%'.format(x))
        display_df.columns  = ['Category', 'Total', 'Transactions', 'Avg Txn', 'Share']
        st.dataframe(display_df, use_container_width=True, hide_index=True)

    # Stacked bar - monthly category breakdown
    if spend_by_cat_df['transaction_month'].nunique() >= 2:
        monthly_cat = spend_by_cat_df.groupby(
            ['transaction_month', 'category']
        )['total_spend'].sum().reset_index().sort_values('transaction_month')

        fig3 = px.bar(monthly_cat, x='transaction_month', y='total_spend',
                      color='category', color_discrete_map=CAT_COLORS,
                      barmode='stack', title='Monthly Spend by Category',
                      labels={
                          'total_spend':        'Spend (₹)',
                          'transaction_month':  'Month',
                          'category':           'Category'
                      })
        fig3.update_traces(marker_line_width=0)
        fig3.update_layout(height=320)
        st.plotly_chart(fig3, use_container_width=True)



# SECTION 3 - MONTHLY TRENDS
  
st.divider()
st.subheader("3 · Monthly Trends")

if has_trends and spend_trends_df['transaction_month'].nunique() >= 2:

    monthly = spend_trends_df.groupby('transaction_month').agg(
        total_spend=('total_spend', 'sum'),
        rolling_avg=('rolling_3m_avg', 'mean'),  
        unique_merchants=('unique_merchants', 'sum'),
        is_anomaly=('is_anomaly', 'max')
    ).reset_index().sort_values('transaction_month')

    monthly['MoM Change'] = monthly['total_spend'].pct_change() * 100

    col_l, col_r = st.columns(2)

    with col_l:
        # Bar + rolling avg line
        fig = make_subplots()
        fig.add_trace(go.Bar(
            x=monthly['transaction_month'],
            y=monthly['total_spend'],
            name='Monthly Spend',
            marker_color='#6C63FF',
            marker_line_width=0,
            opacity=0.85
        ))
        fig.add_trace(go.Scatter(
            x=monthly['transaction_month'],
            y=monthly['rolling_avg'],
            name='3M Rolling Avg (dbt)',
            mode='lines+markers',
            line=dict(color='#FF9500', width=2.5, dash='dot'),
            marker=dict(size=6)
        ))
        # Mark anomaly months
        anomaly_months = monthly[monthly['is_anomaly'] == True]
        if not anomaly_months.empty:
            fig.add_trace(go.Scatter(
                x=anomaly_months['transaction_month'],
                y=anomaly_months['total_spend'],
                name='Anomaly',
                mode='markers',
                marker=dict(color='#FF3B30', size=12, symbol='x')
            ))
        fig.update_layout(
            title='Monthly Spend + 3M Rolling Avg',
            height=320, bargap=0.3
        )
        st.plotly_chart(fig, use_container_width=True)

    with col_r:
        mom = monthly.dropna(subset=['MoM Change'])
        if not mom.empty:
            mom_colors = [
                '#FF3B30' if x > 0 else '#00C853'
                for x in mom['MoM Change']
            ]
            fig2 = go.Figure(go.Bar(
                x=mom['transaction_month'],
                y=mom['MoM Change'],
                marker_color=mom_colors,
                marker_line_width=0,
                text=['{:+.1f}%'.format(x) for x in mom['MoM Change']],
                textposition='outside',
                textfont_size=10
            ))
            fig2.add_hline(y=0, line_width=1.5)
            fig2.update_layout(
                title='Month-on-Month Change (%)',
                height=320, showlegend=False
            )
            st.plotly_chart(fig2, use_container_width=True)

    # Heatmap 
    if spend_by_cat_df['transaction_month'].nunique() >= 3:
        heat_data = spend_by_cat_df.groupby(
            ['transaction_month', 'category']
        )['total_spend'].sum().unstack(fill_value=0).sort_index()

        fig3 = px.imshow(
            heat_data.T,
            color_continuous_scale='Purples',
            aspect='auto',
            title='Spend Heatmap - Category × Month',
            labels=dict(x='Month', y='Category', color='Spend (₹)')
        )
        fig3.update_layout(height=300)
        st.plotly_chart(fig3, use_container_width=True)

elif has_trends:
    st.info("Add at least 2 months of data to see spend trends.")


 
# SECTION 4 - MERCHANT 

st.divider()
st.subheader("4 · Merchant Intelligence")

if has_merchant:
    col_l, col_r = st.columns(2)

    with col_l:
        top_10 = merchant_df.head(10)
        fig = px.bar(top_10, x='total_spend', y='merchant',
                     orientation='h',
                     title='Top 10 Merchants by Total Spend',
                     color='total_spend',
                     color_continuous_scale=['#E0DEFF', '#6C63FF'],
                     text=top_10['total_spend'].apply(fmt),
                     labels={'total_spend': 'Total Spend', 'merchant': ''})
        fig.update_traces(textposition='outside', marker_line_width=0)
        fig.update_layout(
            showlegend=False, coloraxis_showscale=False,
            height=380, yaxis=dict(autorange='reversed')
        )
        st.plotly_chart(fig, use_container_width=True)

    with col_r:
        freq_table = merchant_df.sort_values(
            'total_transactions', ascending=False
        ).head(10)[['merchant', 'total_transactions', 'avg_spend', 'category']].copy()
        freq_table['avg_spend'] = freq_table['avg_spend'].apply(fmt)
        freq_table.columns = ['Merchant', 'Visits', 'Avg Txn', 'Category']
        st.caption("Merchant Frequency + Avg Ticket Size")
        st.dataframe(freq_table, use_container_width=True, hide_index=True)

    # Recurring merchants 
    recurring = merchant_df[merchant_df['months_active'] >= 2]\
        .sort_values('months_active', ascending=False)

    if not recurring.empty:
        st.caption("🔄 Recurring Merchants - detected (active in 2+ months)")
        rec_display = recurring.head(8)[
            ['merchant', 'months_active', 'total_spend',
             'avg_spend', 'category']
        ].copy()
        rec_display['total_spend'] = rec_display['total_spend'].apply(fmt)
        rec_display['avg_spend']   = rec_display['avg_spend'].apply(fmt)
        rec_display.columns = ['Merchant', 'Months Active',
                               'Total Spend', 'Avg/Txn', 'Category']
        st.dataframe(rec_display, use_container_width=True, hide_index=True)

    # Largest single transactions 
    st.caption("💰 Largest Single Transactions (by merchant)")
    big_txns = merchant_df.nlargest(5, 'avg_spend')[
        ['merchant', 'avg_spend', 'total_transactions',
         'category', 'last_transacted']
    ].copy()
    big_txns['avg_spend']      = big_txns['avg_spend'].apply(fmt)
    big_txns['last_transacted'] = pd.to_datetime(
        big_txns['last_transacted']
    ).dt.strftime('%d %b %Y')
    big_txns.columns = ['Merchant', 'Avg Spend', 'Visits',
                        'Category', 'Last Seen']
    st.dataframe(big_txns, use_container_width=True, hide_index=True)



# SECTION 5 - PAYMENT BEHAVIOUR

st.divider()
st.subheader("5 · Payment Behaviour")

if has_recon:
    total_stmts    = len(pay_recon_df)
    paid_stmts     = len(pay_recon_df[pay_recon_df['status'] == 'Paid'])
    partial_stmts  = len(pay_recon_df[pay_recon_df['status'] == 'Partial'])
    unpaid_stmts   = len(pay_recon_df[pay_recon_df['status'] == 'Unpaid'])
    overdue_stmts  = int(pay_recon_df['is_overdue'].sum())
    on_time_rate   = paid_stmts / max(total_stmts, 1) * 100

    # interest_risk flagged 
    at_risk = pay_recon_df[pay_recon_df['interest_risk'] == True]
    total_estimated_interest = pay_recon_df['estimated_interest'].sum()

    c1, c2, c3, c4 = st.columns(4)
    with c1:
        st.metric("Full Payment Rate", '{:.0f}%'.format(on_time_rate),
                  str(paid_stmts) + " of " + str(total_stmts))
    with c2:
        st.metric("Overdue Statements", str(overdue_stmts),
                  delta="Past due date" if overdue_stmts > 0 else None,
                  delta_color="inverse")
    with c3:
        st.metric("At Interest Risk", str(len(at_risk)),
                  "Flagged by dbt",
                  delta_color="inverse" if len(at_risk) > 0 else "off")
    with c4:
        st.metric("Est. Interest Exposure", fmt(total_estimated_interest),
                  "If minimums only paid")

    col_l, col_r = st.columns(2)

    with col_l:
        status_data = pd.DataFrame({
            'Status': ['Paid', 'Partial', 'Unpaid'],
            'Count':  [paid_stmts, partial_stmts, unpaid_stmts]
        })
        status_data = status_data[status_data['Count'] > 0]
        fig = px.pie(status_data, names='Status', values='Count',
                     hole=0.5, color='Status',
                     color_discrete_map={
                         'Paid':    '#00C853',
                         'Partial': '#FF9500',
                         'Unpaid':  '#FF3B30'
                     },
                     title='Statement Payment Status')
        fig.update_traces(textinfo='label+percent', textfont_size=10)
        fig.update_layout(height=280)
        st.plotly_chart(fig, use_container_width=True)

    with col_r:
        fig2 = go.Figure(go.Histogram(
            x=pay_recon_df['payment_progress_pct'].astype(float),
            marker_color='#6C63FF',
            marker_line_width=0,
            opacity=0.8,
            nbinsx=10
        ))
        fig2.add_vline(x=100, line_dash='dash', line_color='#00C853',
                       annotation_text='Fully Paid',
                       annotation_font_size=10)
        fig2.update_layout(
            title='Payment Progress Distribution (%)',
            xaxis_title='% of Statement Paid',
            height=280, showlegend=False
        )
        st.plotly_chart(fig2, use_container_width=True)

    out_trend = pay_recon_df.groupby(
        'statement_month'
    )['closing_balance'].sum().reset_index().sort_values('statement_month')

    if len(out_trend) >= 2:
        fig3 = px.line(out_trend, x='statement_month', y='closing_balance',
                       markers=True, title='Closing Balance Trend by Month',
                       color_discrete_sequence=['#FF3B30'],
                       labels={
                           'closing_balance':  'Closing Balance (₹)',
                           'statement_month':  'Month'
                       })
        fig3.update_traces(line_width=2.5, marker_size=7,
                           fill='tozeroy',
                           fillcolor='rgba(255,59,48,0.08)')
        fig3.update_layout(height=240)
        st.plotly_chart(fig3, use_container_width=True)

    # Interest risk
    if not at_risk.empty:
        st.warning("⚠️ **" + str(len(at_risk)) + " statement(s)** at interest risk - "
                   "minimum due paid but balance carried forward.")
        risk_display = at_risk[[
            'card_display_name', 'statement_month',
            'closing_balance', 'minimum_due', 'estimated_interest'
        ]].copy()
        risk_display['closing_balance']    = risk_display['closing_balance'].apply(fmt)
        risk_display['minimum_due']        = risk_display['minimum_due'].apply(fmt)
        risk_display['estimated_interest'] = risk_display['estimated_interest'].apply(fmt)
        risk_display.columns = ['Card', 'Month', 'Balance',
                                'Min Due', 'Est. Interest']
        st.dataframe(risk_display, use_container_width=True, hide_index=True)

else:
    st.info("Upload statements to see payment behaviour analysis.")


 
# SECTION 6 - CREDIT HEALTH

st.divider()
st.subheader("6 · Credit Health")

if has_summary:
    # Latest statement per card
    latest_per_card = monthly_summary_df.sort_values(
        'due_date', ascending=False
    ).drop_duplicates(subset='card_id')

    # Shared pool utilization 
    util_rows = []

    for g in shared_groups:
        util_rows.append({
            'name':  str(g['group_name']),
            'used':  float(g['total_used']),
            'limit': float(g['total_limit']),
            'pct':   float(g['utilization_pct']),
            'type':  'Pool'
        })

    # Independent cards 
    pool_card_ids = set()
    for g in shared_groups:
        for c in g.get('cards', []):
            pool_card_ids.add(c['id'])

    if not spend_trends_df.empty:
        # Get latest month per card for current utilization
        latest_per_card = spend_trends_df.sort_values(
            'transaction_month', ascending=False
        ).drop_duplicates(subset='card_id')

        for _, row in latest_per_card.iterrows():
            if int(row['card_id']) not in pool_card_ids:

                util_rows.append({
                    'name':  str(row['card_display_name']),
                    'used':  float(row['total_spend']),
                    'limit': float(row['total_spend']) * 2,  
                    'pct':   0.0,
                    'type':  'Card'
                })

    if util_rows:
        util_df_local = pd.DataFrame(util_rows).sort_values(
            'pct', ascending=False
        )
        total_used  = util_df_local['used'].sum()
        total_limit = util_df_local['limit'].sum()
        overall_pct = (total_used / total_limit * 100) if total_limit > 0 else 0

        c1, c2, c3 = st.columns(3)
        with c1:
            st.metric("Overall Utilization", '{:.1f}%'.format(overall_pct))
        with c2:
            st.metric("Total Used", fmt(total_used))
        with c3:
            st.metric("Total Available", fmt(total_limit - total_used))

        st.progress(min(overall_pct / 100, 1.0))

        col_l, col_r = st.columns(2)

        with col_l:
            gauge_color = (
                '#FF3B30' if overall_pct > 80
                else '#FF9500' if overall_pct > 50
                else '#00C853'
            )
            fig = go.Figure(go.Indicator(
                mode="gauge+number",
                value=overall_pct,
                number={'suffix': '%'},
                gauge=dict(
                    axis=dict(range=[0, 100]),
                    bar=dict(color=gauge_color, thickness=0.6),
                    steps=[
                        dict(range=[0,  50], color='#F0FFF4'),
                        dict(range=[50, 80], color='#FFFBEB'),
                        dict(range=[80, 100], color='#FFF1F0')
                    ],
                    threshold=dict(
                        line=dict(color='red', width=2),
                        thickness=0.7, value=80
                    )
                ),
                title={'text': 'Overall Credit Utilization'}
            ))
            fig.update_layout(height=280, margin=dict(l=20, r=20, t=40, b=20))
            st.plotly_chart(fig, use_container_width=True)

        with col_r:
            bar_colors = [
                '#FF3B30' if p > 80 else '#FF9500' if p > 50 else '#0EA5E9'
                for p in util_df_local['pct']
            ]
            fig2 = go.Figure(go.Bar(
                x=util_df_local['pct'], y=util_df_local['name'],
                orientation='h', marker_color=bar_colors,
                marker_line_width=0,
                text=['{:.1f}%'.format(p) for p in util_df_local['pct']],
                textposition='outside', textfont_size=10
            ))
            fig2.add_vline(x=80, line_dash='dash', line_color='#FF3B30',
                           line_width=1, annotation_text='80% threshold',
                           annotation_font_size=9)
            fig2.update_layout(
                title='Utilization by Card / Pool',
                height=320, showlegend=False,
                xaxis=dict(range=[0, 115]),
                yaxis=dict(autorange='reversed')
            )
            st.plotly_chart(fig2, use_container_width=True)

        # Utilization trend over months 
        if monthly_summary_df['statement_month'].nunique() >= 2:
            util_trend = monthly_summary_df.groupby(
                'statement_month'
            )['utilization_pct'].mean().reset_index().sort_values('statement_month')

            fig3 = px.line(util_trend, x='statement_month', y='utilization_pct',
                           markers=True,
                           title='Avg Utilization Trend by Month (dbt)',
                           color_discrete_sequence=['#6C63FF'],
                           labels={
                               'utilization_pct':  'Utilization (%)',
                               'statement_month':  'Month'
                           })
            fig3.add_hline(y=30, line_dash='dot', line_color='#00C853',
                           annotation_text='Ideal ≤30%', annotation_font_size=9)
            fig3.add_hline(y=80, line_dash='dot', line_color='#FF3B30',
                           annotation_text='Danger >80%', annotation_font_size=9)
            fig3.update_traces(line_width=2.5, marker_size=7)
            fig3.update_layout(height=260)
            st.plotly_chart(fig3, use_container_width=True)

else:
    st.info("Upload statements to see credit health data.")



# SECTION 7 - LOAN ANALYTICS

st.divider()
st.subheader("7 · Loan Analytics")

if has_loans:
    active_loans = loan_df[loan_df['status'] == 'Active'].copy()

    if not active_loans.empty:
        active_loans['outstanding_principal'] = active_loans['outstanding_principal'].astype(float)
        active_loans['emi_amount']            = active_loans['emi_amount'].astype(float)
        active_loans['principal_amount']      = active_loans['principal_amount'].astype(float)
        active_loans['total_paid']            = active_loans['total_paid'].astype(float)

        total_outstanding = active_loans['outstanding_principal'].sum()
        total_emi         = active_loans['emi_amount'].sum()
        total_principal   = active_loans['principal_amount'].sum()
        total_paid_loans  = active_loans['total_paid'].sum()
        overall_pct       = (total_paid_loans / total_principal * 100
                             if total_principal > 0 else 0)

        total_interest_rem = sum(
            float(row['emi_amount'])
            * max(0, int(row['tenure_months']) - max(0, (
                (today.year - pd.to_datetime(row['start_date']).year) * 12
                + today.month - pd.to_datetime(row['start_date']).month
            )))
            - float(row['outstanding_principal'])
            for _, row in active_loans.iterrows()
        )

        c1, c2, c3, c4 = st.columns(4)
        with c1:
            st.metric("Total Outstanding", fmt(total_outstanding))
        with c2:
            st.metric("Monthly EMI Burden", fmt(total_emi),
                      str(len(active_loans)) + " active loans")
        with c3:
            st.metric("Overall Progress", '{:.1f}%'.format(overall_pct),
                      fmt(total_paid_loans) + " paid")
        with c4:
            st.metric("Interest Remaining", fmt(max(total_interest_rem, 0)),
                      "Estimated")

        col_l, col_r = st.columns(2)

        with col_l:
            loan_names      = []
            pct_paid_list   = []
            pct_remain_list = []
            for _, row in active_loans.iterrows():
                name = (str(row['loan_nickname']) if row['loan_nickname']
                        else str(row['lender_name']))
                loan_names.append(name)
                pct = float(row['pct_paid'] or 0)
                pct_paid_list.append(pct)
                pct_remain_list.append(100 - pct)

            fig = go.Figure()
            fig.add_trace(go.Bar(
                name='Paid', x=pct_paid_list, y=loan_names,
                orientation='h', marker_color='#00C853',
                marker_line_width=0,
                text=['{:.1f}%'.format(p) for p in pct_paid_list],
                textposition='inside',
                textfont=dict(color='white', size=10)
            ))
            fig.add_trace(go.Bar(
                name='Remaining', x=pct_remain_list, y=loan_names,
                orientation='h', marker_color='#F0F0F5',
                marker_line_width=0
            ))
            fig.update_layout(
                title='Loan Repayment Progress',
                barmode='stack', height=280, bargap=0.3,
                xaxis=dict(range=[0, 100])
            )
            st.plotly_chart(fig, use_container_width=True)

        with col_r:
            payoff_rows = []
            for _, row in active_loans.iterrows():
                name = (str(row['loan_nickname']) if row['loan_nickname']
                        else str(row['lender_name']))
                try:
                    start = pd.to_datetime(row['start_date']).date()
                    elapsed    = max(0, (today.year - start.year) * 12
                                     + today.month - start.month)
                    months_left = max(0, int(row['tenure_months']) - elapsed)
                    end_date = date(
                        today.year + (today.month + months_left - 1) // 12,
                        (today.month + months_left - 1) % 12 + 1, 1
                    )
                    payoff_rows.append({
                        'Loan': name,
                        'Months Left': months_left,
                        'End Date': end_date.strftime('%b %Y')
                    })
                except:
                    pass

            if payoff_rows:
                pdf = pd.DataFrame(payoff_rows)
                fig2 = px.bar(pdf, x='Months Left', y='Loan',
                              orientation='h', color='Months Left',
                              color_continuous_scale=['#00C853', '#FF9500', '#FF3B30'],
                              text='End Date',
                              title='Projected Payoff Timeline')
                fig2.update_traces(textposition='outside', marker_line_width=0)
                fig2.update_layout(coloraxis_showscale=False,
                                   showlegend=False, height=280)
                st.plotly_chart(fig2, use_container_width=True)

        if not loan_pay_df.empty:
            monthly_pi = loan_pay_df.groupby(
                ['month_key', 'month_label']
            ).agg(
                principal=('principal_component', 'sum'),
                interest=('interest_component', 'sum')
            ).reset_index().sort_values('month_key')

            col_l2, col_r2 = st.columns(2)
            with col_l2:
                fig3 = go.Figure()
                fig3.add_trace(go.Bar(
                    name='Principal', x=monthly_pi['month_label'],
                    y=monthly_pi['principal'],
                    marker_color='#00C853', marker_line_width=0
                ))
                fig3.add_trace(go.Bar(
                    name='Interest', x=monthly_pi['month_label'],
                    y=monthly_pi['interest'],
                    marker_color='#FF3B30', marker_line_width=0
                ))
                fig3.update_layout(
                    title='Monthly EMI - Principal vs Interest',
                    barmode='group', height=280
                )
                st.plotly_chart(fig3, use_container_width=True)

            with col_r2:
                total_p = float(loan_pay_df['principal_component'].sum())
                total_i = float(loan_pay_df['interest_component'].sum())
                pi_data = pd.DataFrame({
                    'Component': ['Principal Paid', 'Interest Paid'],
                    'Amount':    [total_p, total_i]
                })
                fig4 = px.pie(pi_data, names='Component', values='Amount',
                              hole=0.5, title='Principal vs Interest - Paid to Date',
                              color='Component',
                              color_discrete_map={
                                  'Principal Paid': '#00C853',
                                  'Interest Paid':  '#FF3B30'
                              })
                fig4.update_traces(textinfo='label+percent', textfont_size=10)
                fig4.update_layout(height=280)
                st.plotly_chart(fig4, use_container_width=True)

        # Prepayment Impact Calculator
        st.subheader("Prepayment Impact Calculator")
        loan_options = {
            (str(row['loan_nickname']) if row['loan_nickname']
             else str(row['lender_name'])): int(row['id'])
            for _, row in active_loans.iterrows()
        }

        col_s, col_e = st.columns(2)
        with col_s:
            sel_loan_name = st.selectbox(
                "Select Loan", list(loan_options.keys()),
                key="prepay_loan"
            )
        with col_e:
            extra_payment = st.number_input(
                "Extra Monthly Payment (₹)",
                min_value=0, value=1000, step=500,
                key="prepay_extra"
            )

        sel_loan_id     = loan_options[sel_loan_name]
        sel_row         = active_loans[active_loans['id'] == sel_loan_id].iloc[0]
        outstanding_now = float(sel_row['outstanding_principal'])
        rate            = float(sel_row['interest_rate'])
        emi_now         = float(sel_row['emi_amount'])
        tenure          = int(sel_row['tenure_months'])
        monthly_rate    = rate / 12 / 100

        try:
            start = pd.to_datetime(sel_row['start_date']).date()
            elapsed     = max(0, (today.year - start.year) * 12
                               + today.month - start.month)
            months_left = max(0, tenure - elapsed)
        except:
            months_left = tenure

        def months_to_payoff(principal, monthly_rate, emi):
            if emi <= 0 or monthly_rate <= 0:
                return months_left
            bal = principal
            m   = 0
            while bal > 0 and m < 600:
                interest       = bal * monthly_rate
                principal_comp = emi - interest
                if principal_comp <= 0:
                    return 600
                bal -= principal_comp
                m   += 1
            return m

        std_months   = months_to_payoff(outstanding_now, monthly_rate, emi_now)
        extra_months = months_to_payoff(outstanding_now, monthly_rate,
                                        emi_now + extra_payment)
        months_saved   = max(std_months - extra_months, 0)
        interest_saved = max(
            emi_now * std_months - outstanding_now
            - (emi_now + extra_payment) * extra_months + outstanding_now,
            0
        )

        if extra_payment > 0:
            c1, c2, c3 = st.columns(3)
            with c1:
                st.metric("Months Saved", str(months_saved))
            with c2:
                st.metric("Interest Saved", fmt(interest_saved))
            with c3:
                st.metric("New Payoff", str(extra_months) + " months")

else:
    st.info("No loan data found. Add loans on the Loans page.")



# SECTION 8 - SMART OBSERVATIONS

st.divider()
st.subheader("8 · Smart Observations")

observations = []

# Spend trend MoM 
if has_trends and spend_trends_df['transaction_month'].nunique() >= 2:
    monthly_agg = spend_trends_df.groupby(
        'transaction_month'
    )['total_spend'].sum().sort_index()
    if len(monthly_agg) >= 2:
        last_m   = monthly_agg.iloc[-1]
        prev_m   = monthly_agg.iloc[-2]
        last_lbl = monthly_agg.index[-1]
        prev_lbl = monthly_agg.index[-2]
        pct_chg  = (last_m - prev_m) / prev_m * 100 if prev_m > 0 else 0
        if abs(pct_chg) >= 5:
            direction = 'increased' if pct_chg > 0 else 'decreased'
            observations.append(
                ('📈 ' if pct_chg > 0 else '📉 ')
                + 'Spend **' + direction
                + '** by {:.1f}% in '.format(abs(pct_chg))
                + last_lbl + ' vs ' + prev_lbl
                + ' (' + fmt(prev_m) + ' → ' + fmt(last_m) + ')'
            )

# Anomaly months 
if has_trends:
    anomaly_rows = spend_trends_df[spend_trends_df['is_anomaly'] == True]
    if not anomaly_rows.empty:
        anomaly_cards = anomaly_rows['card_display_name'].unique()
        observations.append(
            '🚨 Flagged **' + str(len(anomaly_rows))
            + ' month(s)** as spend anomalies across: '
            + ', '.join(anomaly_cards)
        )

# Top category from spend_by_category mart 
if has_cat:
    latest_month = spend_by_cat_df['transaction_month'].max()
    latest_cat   = spend_by_cat_df[
        spend_by_cat_df['transaction_month'] == latest_month
    ]
    if not latest_cat.empty:
        top_cat     = latest_cat.loc[latest_cat['total_spend'].idxmax()]
        observations.append(
            '🏷️ **' + str(top_cat['category'])
            + '** was your biggest category in '
            + latest_month + ' at **'
            + fmt(top_cat['total_spend']) + '**'
        )

# Recurring merchants 
if has_merchant:
    recurring_count = len(merchant_df[merchant_df['months_active'] >= 2])
    recurring_spend = merchant_df[
        merchant_df['months_active'] >= 2
    ]['avg_spend'].sum()
    if recurring_count > 0:
        observations.append(
            '🔄 **' + str(recurring_count)
            + ' recurring merchants** detected - '
            + 'averaging ' + fmt(recurring_spend) + ' per visit'
        )

#Interest risk 
if has_recon:
    at_risk_count = int(pay_recon_df['interest_risk'].sum())
    est_interest  = float(pay_recon_df['estimated_interest'].sum())
    if at_risk_count > 0:
        observations.append(
            '⚠️ **' + str(at_risk_count)
            + ' statement(s)** at interest risk - '
            'estimated interest exposure: **' + fmt(est_interest) + '**'
        )

# High utilization 
if has_summary:
    latest_per_card_obs = monthly_summary_df.sort_values(
        'due_date', ascending=False
    ).drop_duplicates(subset='card_id')
    high_util = latest_per_card_obs[
        latest_per_card_obs['utilization_pct'].astype(float) > 80
    ]
    for _, row in high_util.iterrows():
        observations.append(
            '⚠️ **' + str(row['card_display_name'])
            + '** is at {:.1f}%'.format(float(row['utilization_pct']))
            + ' utilization - approaching credit limit'
        )

# Loan observations from raw tables
if has_loans and not active_loans.empty:
    for _, row in active_loans.iterrows():
        name = (str(row['loan_nickname']) if row['loan_nickname']
                else str(row['lender_name']))
        try:
            start = pd.to_datetime(row['start_date']).date()
            elapsed = max(0, (today.year - start.year) * 12
                          + today.month - start.month)
            months_left = max(0, int(row['tenure_months']) - elapsed)
            observations.append(
                '🏦 **' + name + '** - '
                + str(months_left) + ' months remaining, outstanding: **'
                + fmt(row['outstanding_principal']) + '**'
            )
        except:
            pass

if observations:
    col_l, col_r = st.columns(2)
    for i, obs in enumerate(observations):
        with (col_l if i % 2 == 0 else col_r):
            st.info(obs)
else:
    st.info("Add more data and run dbt to generate smart observations.")