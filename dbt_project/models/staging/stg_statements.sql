-- Staging model for statements


with source as (
    select * from {{ source('raw', 'statements') }}
),

cleaned as (
    select
        id                                          as statement_id,
        card_id,
        statement_month,
        statement_date,
        statement_period_start,
        statement_period_end,
        due_date,

        coalesce(total_amount, 0)                   as total_amount,
        coalesce(minimum_due, 0)                    as minimum_due,
        coalesce(opening_balance, 0)                as opening_balance,
        coalesce(amount_paid, 0)                    as amount_paid,
        coalesce(outstanding, total_amount)         as outstanding,

        status,
        pdf_link,


        due_date - current_date                     as days_until_due,

        case
            when due_date < current_date
            and status != 'Paid'
            then true
            else false
        end                                         as is_overdue,

        case
            when due_date - current_date <= 7
            and due_date >= current_date
            and status != 'Paid'
            then true
            else false
        end                                         as is_due_soon,

        case
            when total_amount > 0
            then round((coalesce(amount_paid, 0) / total_amount * 100)::numeric, 2)
            else 0
        end                                         as payment_progress_pct,

        case
            when statement_period_start is not null
            and statement_period_end is not null
            then to_char(statement_period_start, 'DD Mon YYYY')
                 || ' to '
                 || to_char(statement_period_end, 'DD Mon YYYY')
            else statement_month
        end                                         as billing_period_display

    from source
)

select * from cleaned