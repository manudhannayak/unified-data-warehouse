with source as (
    select * from {{ source('raw', 'product_usage_events') }}
)

select
    event_id,
    account_id,
    event_type,
    cast(event_timestamp as timestamp) as event_timestamp
from source
