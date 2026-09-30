-- The "unified" mart: one row per account combining CRM, billing, and
-- product-usage signals -- the whole point of the warehouse. This is what
-- a CS/RevOps team would actually query or plug into a BI dashboard.

with accounts as (
    select * from {{ ref('dim_accounts') }}
),

lifetime_revenue as (
    select
        account_id,
        sum(paid_revenue_usd) as lifetime_paid_revenue_usd,
        sum(unpaid_revenue_usd) as lifetime_unpaid_revenue_usd
    from {{ ref('fct_revenue_monthly') }}
    group by 1
),

recent_engagement as (
    select
        account_id,
        sum(total_events) as total_events_all_time,
        max(event_month) as last_active_month
    from {{ ref('fct_engagement_monthly') }}
    group by 1
)

select
    a.account_id,
    a.account_name,
    a.industry,
    a.region,
    a.plan,
    a.created_at,
    a.account_age_days,
    a.is_churned,
    coalesce(r.lifetime_paid_revenue_usd, 0) as lifetime_paid_revenue_usd,
    coalesce(r.lifetime_unpaid_revenue_usd, 0) as lifetime_unpaid_revenue_usd,
    coalesce(e.total_events_all_time, 0) as total_events_all_time,
    e.last_active_month
from accounts a
left join lifetime_revenue r on a.account_id = r.account_id
left join recent_engagement e on a.account_id = e.account_id
