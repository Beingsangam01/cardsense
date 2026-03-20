-- Top merchants by spend
-- Powers merchant leaderboard and subscription detection

with transactions as (
    select * from {{ ref('stg_transactions') }}
),

cards as (
    select * from {{ ref('stg_cards') }}
),

final as (
    select
        t.merchant,
        t.category,
        t.card_id,
        c.card_display_name,
        c.bank_name,

        -- Overall stats
        count(*)                                    as total_transactions,
        sum(t.debit_amount)                         as total_spend,
        avg(t.debit_amount)                         as avg_spend,
        max(t.transaction_date)                     as last_transacted,
        min(t.transaction_date)                     as first_transacted,

        -- EMI and subscription flags
        max(case when t.is_emi = 'yes' then 1 else 0 end)          as has_emi,
        max(case when t.is_subscription = 'yes' then 1 else 0 end) as has_subscription,

        -- Number of months this merchant appeared
        count(distinct t.transaction_month)         as months_active

    from transactions t
    left join cards c on t.card_id = c.card_id
    where t.transaction_type = 'debit'
    group by
        t.merchant,
        t.category,
        t.card_id,
        c.card_display_name,
        c.bank_name
)

select * from final
order by total_spend desc