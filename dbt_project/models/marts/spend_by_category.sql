-- Spending breakdown by category
-- Powers the category pie chart and insights

with transactions as (
    select * from {{ ref('stg_transactions') }}
    where transaction_type = 'debit'
),

cards as (
    select * from {{ ref('stg_cards') }}
),

final as (
    select
        t.card_id,
        c.card_display_name,
        c.bank_name,
        t.transaction_month,
        t.category,
        count(*)                        as transaction_count,
        sum(t.debit_amount)             as total_spend,
        avg(t.debit_amount)             as avg_transaction,
        max(t.debit_amount)             as max_transaction,
        min(t.debit_amount)             as min_transaction

    from transactions t
    left join cards c on t.card_id = c.card_id
    group by
        t.card_id,
        c.card_display_name,
        c.bank_name,
        t.transaction_month,
        t.category
)

select * from final
order by transaction_month desc, total_spend desc