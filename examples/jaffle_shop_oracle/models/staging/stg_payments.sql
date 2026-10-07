-- Reprise telle quelle d'une vue Oracle : montants agrégés par commande.
select
    p.order_id,
    sum(decode(p.payment_method, 'credit_card', p.amount, 0)) / 100 as credit_card_amount,
    sum(decode(p.payment_method, 'coupon', p.amount, 0)) / 100 as coupon_amount,
    sum(decode(p.payment_method, 'bank_transfer', p.amount, 0)) / 100 as bank_transfer_amount,
    sum(decode(p.payment_method, 'gift_card', p.amount, 0)) / 100 as gift_card_amount,
    sum(nvl(p.amount, 0)) / 100 as amount
from {{ source('jaffle', 'raw_payments') }} p, {{ source('jaffle', 'raw_orders') }} o
where p.order_id = o.id(+)
group by p.order_id
