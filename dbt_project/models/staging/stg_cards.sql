-- Staging model for cards
-- Cleans and standardizes the raw cards table

with source as (
    select * from {{ source('raw', 'cards') }}
),

cleaned as (
    select
        id                                      as card_id,
        bank_name,
        card_nickname,
        last_four_digits,
        statement_day,
        due_day,
        coalesce(credit_limit, 0)               as credit_limit,
        email_sender,
        is_active,

        -- Create a display name combining bank and nickname
        bank_name || ' ' || card_nickname       as card_display_name,

        -- Create a masked card number for display
        '•••• ' || last_four_digits             as masked_card_number

    from source
    where is_active = 'yes'
)

select * from cleaned