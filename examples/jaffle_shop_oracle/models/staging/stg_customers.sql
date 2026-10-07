with source as (
    select * from {{ source('jaffle', 'raw_customers') }}
),

renamed as (
    select
        id as customer_id,
        initcap(first_name) as first_name,
        initcap(last_name) as last_name
    from source
)

select * from renamed
