-- Statement vs payments reconciliation
-- Shows exactly what was billed, what was paid, what's outstanding

with statements as (
    select * from {{ ref('stg_statements') }}
),

cards as (
    select * from {{ ref('stg_cards') }}
),

payments as (
    select * from {{ ref('stg_payments') }}
),

payment_details as (
    select
        statement_id,
        json_agg(
            json_build_object(
                'payment_date', payment_date,
                'amount', payment_amount,
                'type', payment_type,
                'reference', reference_number
            ) order by payment_date
        ) as payment_breakdown
    from payments
    group by statement_id
),

final as (
    select
        s.statement_id,
        s.card_id,
        c.card_display_name,
        c.bank_name,
        c.masked_card_number,

        s.statement_month,
        s.billing_period_display,
        s.due_date,
        s.status,
        s.is_overdue,
        s.days_until_due,

        -- The reconciliation breakdown
        s.opening_balance,
        s.total_amount                              as charges_this_period,
        s.amount_paid                               as payments_received,
        s.outstanding                               as closing_balance,
        s.minimum_due,
        s.payment_progress_pct,

        -- Risk flag — only minimum paid means interest will accrue
        case
            when s.status = 'Partial'
            and s.amount_paid <= s.minimum_due
            then true
            else false
        end                                         as interest_risk,

        -- Estimated monthly interest at 3.5% if not paid in full
        case
            when s.status != 'Paid'
            then round((s.outstanding * 0.035)::numeric, 2)
            else 0
        end                                         as estimated_interest,

        pd.payment_breakdown

    from statements s
    left join cards c on s.card_id = c.card_id
    left join payment_details pd on s.statement_id = pd.statement_id
)

select * from final
order by due_date desc