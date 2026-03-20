-- One row per card per month


with statements as (
    select * from {{ ref('stg_statements') }}
),

cards as (
    select * from {{ ref('stg_cards') }}
),

payments as (
    select
        statement_id,
        sum(payment_amount)     as total_paid,
        count(*)                as payment_count,
        max(payment_date)       as last_payment_date
    from {{ ref('stg_payments') }}
    group by statement_id
),

final as (
    select
        s.statement_id,
        s.card_id,
        c.bank_name,
        c.card_nickname,
        c.card_display_name,
        c.masked_card_number,
        c.credit_limit,

        s.statement_month,
        s.billing_period_display,
        s.statement_date,
        s.due_date,
        s.days_until_due,
        s.is_overdue,
        s.is_due_soon,

        s.total_amount,
        s.minimum_due,
        s.opening_balance,
        coalesce(p.total_paid, 0)       as total_paid,
        s.outstanding,
        s.payment_progress_pct,
        s.status,
        s.pdf_link,

        coalesce(p.payment_count, 0)    as payment_count,
        p.last_payment_date,

        case
            when c.credit_limit > 0
            then round((s.total_amount / c.credit_limit * 100)::numeric, 2)
            else null
        end                             as utilization_pct

    from statements s
    left join cards c on s.card_id = c.card_id
    left join payments p on s.statement_id = p.statement_id
)

select * from final