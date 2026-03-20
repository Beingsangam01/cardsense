-- Month over month spend trends per card


with transactions as (
    select * from {{ ref('stg_transactions') }}
    where transaction_type = 'debit'
),

cards as (
    select * from {{ ref('stg_cards') }}
),

monthly as (
    select
        t.card_id,
        c.card_display_name,
        c.bank_name,
        t.transaction_month,
        date_trunc('month', t.transaction_date)     as month_start,
        count(*)                                    as transaction_count,
        sum(t.debit_amount)                         as total_spend,
        avg(t.debit_amount)                         as avg_transaction,
        count(distinct t.merchant)                  as unique_merchants,
        count(case when t.is_emi = 'yes' then 1 end)        as emi_count,
        sum(case when t.is_emi = 'yes' then t.debit_amount else 0 end) as emi_spend,
        count(case when t.is_subscription = 'yes' then 1 end) as subscription_count,
        sum(case when t.is_subscription = 'yes' then t.debit_amount else 0 end) as subscription_spend

    from transactions t
    left join cards c on t.card_id = c.card_id
    group by
        t.card_id,
        c.card_display_name,
        c.bank_name,
        t.transaction_month,
        date_trunc('month', t.transaction_date)
),

-- 3 month rolling average for anomaly detection
with_rolling_avg as (
    select
        *,
        avg(total_spend) over (
            partition by card_id
            order by month_start
            rows between 2 preceding and 1 preceding
        )                                           as rolling_3m_avg,

        -- we will SFlag if current month is more than 50% above rolling average
        case
            when avg(total_spend) over (
                partition by card_id
                order by month_start
                rows between 2 preceding and 1 preceding
            ) > 0
            and total_spend > avg(total_spend) over (
                partition by card_id
                order by month_start
                rows between 2 preceding and 1 preceding
            ) * 1.5
            then true
            else false
        end                                         as is_anomaly

    from monthly
)

select * from with_rolling_avg
order by card_id, month_start desc