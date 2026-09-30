with source as (
    select * from {{ source('raw', 'crm_accounts') }}
)

select
    account_id,
    account_name,
    lower(industry) as industry,
    region,
    lower(plan) as plan,
    cast(created_at as date) as created_at,
    is_churned
from source
