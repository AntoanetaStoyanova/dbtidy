select
    o.order_id,
    o.customer_id,
    o.order_date,
    o.status,
    nvl(p.credit_card_amount, 0) as credit_card_amount,
    nvl(p.coupon_amount, 0) as coupon_amount,
    nvl(p.bank_transfer_amount, 0) as bank_transfer_amount,
    nvl(p.gift_card_amount, 0) as gift_card_amount,
    nvl(p.amount, 0) as amount
from {{ ref('stg_orders') }} o, {{ ref('stg_payments') }} p
where o.order_id = p.order_id(+)  -- noqa: ORA001
