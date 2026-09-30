with source as (
    select * from {{ source('raw', 'billing_invoices') }}
)

select
    invoice_id,
    account_id,
    cast(invoice_date as date) as invoice_date,
    amount_usd,
    paid
from source
