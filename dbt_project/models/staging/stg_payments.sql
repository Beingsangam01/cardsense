-- Staging model for payments

with source as (
    select * from {{ source('raw', 'payments') }}
),

cleaned as (
    select
        id                                          as payment_id,
        card_id,
        statement_id,
        payment_date,
        amount                                      as payment_amount,
        payment_type,
        coalesce(reference_number, 'N/A')           as reference_number,
        coalesce(notes, '')                         as notes,

        -- Month and year for grouping
        to_char(payment_date, 'Mon YYYY')           as payment_month

    from source
)

select * from cleaned