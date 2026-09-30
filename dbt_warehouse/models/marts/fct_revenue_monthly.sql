with invoices as (
    select * from {{ ref('stg_billing_invoices') }}
)

select
    account_id,
    date_trunc('month', invoice_date) as revenue_month,
    sum(amount_usd) filter (where paid) as paid_revenue_usd,
    sum(amount_usd) filter (where not paid) as unpaid_revenue_usd,
    count(*) as invoice_count
from invoices
group by 1, 2
