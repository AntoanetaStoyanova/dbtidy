with customers as (
    select * from {{ ref('stg_customers') }}
),

orders as (
    select * from {{ ref('stg_orders') }}
),

customer_orders as (
    select
        customer_id,
        min(order_date) as first_order,
        max(order_date) as most_recent_order,
        count(order_id) as number_of_orders
    from orders
    group by customer_id
)

select
    c.customer_id,
    c.first_name,
    c.last_name,
    co.first_order,
    co.most_recent_order,
    nvl(co.number_of_orders, 0) as number_of_orders,
    trunc(sysdate) - co.most_recent_order as days_since_last_order
from customers c, customer_orders co
where c.customer_id = co.customer_id(+)
