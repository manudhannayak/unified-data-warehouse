with events as (
    select * from {{ ref('stg_product_usage_events') }}
)

select
    account_id,
    date_trunc('month', event_timestamp) as event_month,
    count(*) as total_events,
    count(distinct event_type) as distinct_event_types,
    count(*) filter (where event_type = 'login') as login_count
from events
group by 1, 2
