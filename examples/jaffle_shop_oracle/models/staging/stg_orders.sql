{{ config(materialized='view') }}

select
    id as order_id,
    user_id as customer_id,
    to_date(order_date, 'YYYY-MM-DD') as order_date,
    decode(status, 'return_pending', 'returned', status) as status
from {{ source('jaffle', 'raw_orders') }}
