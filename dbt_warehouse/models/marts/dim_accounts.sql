with accounts as (
    select * from {{ ref('stg_crm_accounts') }}
)

select
    account_id,
    account_name,
    industry,
    region,
    plan,
    created_at,
    is_churned,
    date_diff('day', created_at, current_date) as account_age_days
from accounts
