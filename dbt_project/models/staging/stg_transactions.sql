-- Staging model for transactions

with source as (
    select * from {{ source('raw', 'transactions') }}
),

cleaned as (
    select
        id                                          as transaction_id,
        statement_id,
        card_id,
        transaction_date,
        transaction_time,

        trim(merchant)                              as merchant,
        description,

        case
            when transaction_type = 'debit'
            then amount
            else 0
        end                                         as debit_amount,

        case
            when transaction_type = 'credit'
            then amount
            else 0
        end                                         as credit_amount,

        amount,
        transaction_type,
        category,
        is_emi,
        is_subscription,

        case
            when transaction_time is not null
            then transaction_date::timestamp + transaction_time::interval
            else transaction_date::timestamp
        end                                         as transaction_timestamp,

        to_char(transaction_date, 'Day')            as day_of_week,

        to_char(transaction_date, 'Mon YYYY')       as transaction_month

    from source
)

select * from cleaned