-- models/core_texi.sql
{{ config(
    materialized='table',
    unique_id='unique_id'
) }}


with transformed as (
SELECT
    md5(
        concat(
            "VendorID", 
            '-', 
            "tpep_pickup_datetime", 
            '-', 
            "tpep_dropoff_datetime",
            '-',
            "passenger_count",
            '-',
            "RateCodeID",
            '-',
            "payment_type",
            '-',
            "dropoff_longitude",
            '-',
            "dropoff_latitude",
            '-',
            "fare_amount"

        )
    ) AS unique_id,
    CAST(current_date AS DATE) AS ingestion_date,
    CAST("VendorID" AS INTEGER) AS vendor_id,
    CAST("tpep_pickup_datetime" AS TIMESTAMP) AS pickup_datetime,
    CAST("tpep_dropoff_datetime" AS TIMESTAMP) AS dropoff_datetime,
    CAST("passenger_count" AS INTEGER) AS passenger_count,
    CAST("trip_distance" AS FLOAT) AS trip_distance,
    CAST("pickup_longitude" AS FLOAT) AS pickup_longitude,
    CAST("pickup_latitude" AS FLOAT) AS pickup_latitude,
    CAST("RateCodeID" AS INTEGER) AS rate_code_id,
    store_and_fwd_flag,
    CAST("dropoff_longitude" AS FLOAT) AS dropoff_longitude,
    CAST("dropoff_latitude" AS FLOAT) AS dropoff_latitude,
    CAST("payment_type" AS INTEGER) AS payment_type,
    CAST("fare_amount" AS FLOAT) AS fare_amount,
    CAST("extra" AS FLOAT) AS extra,
    CAST("mta_tax" AS FLOAT) AS mta_tax,
    CAST("tip_amount" AS FLOAT) AS tip_amount,
    CAST("tolls_amount" AS FLOAT) AS tolls_amount,
    CAST("improvement_surcharge" AS FLOAT) AS improvement_surcharge,
    CAST("total_amount" AS FLOAT) AS total_amount
FROM {{ ref('raw_texi') }}
WHERE
    "tpep_pickup_datetime" IS NOT NULL
    AND "tpep_dropoff_datetime" IS NOT NULL
),
unique_records as(
    select 
        *,
        row_number() over(partition by unique_id order by ingestion_date desc) as row_number
    from transformed
)
select
    unique_id,
    ingestion_date,
    vendor_id,
    pickup_datetime,
    dropoff_datetime,
    passenger_count,
    trip_distance,
    pickup_longitude,
    pickup_latitude,
    rate_code_id,
    dropoff_longitude,
    dropoff_latitude,
    payment_type,
    fare_amount,
    extra,
    mta_tax,
    tip_amount,
    tolls_amount,
    improvement_surcharge,
    total_amount,
    store_and_fwd_flag,
    -- Calculate trip duration in minutes
    EXTRACT(EPOCH FROM dropoff_datetime - pickup_datetime) / 60 as trip_duration_minutes,
    -- Calculate average speed in miles per hour (if trip_distance and duration > 0)
    case
        when trip_distance > 0 and EXTRACT(EPOCH FROM dropoff_datetime - pickup_datetime) > 0
        then trip_distance / (EXTRACT(EPOCH FROM dropoff_datetime - pickup_datetime) / 3600)
        else null
    end as avg_speed_mph,
    -- Flag for long trips (over 10 miles)
    case
        when trip_distance > 10 then true
        else false
    end as is_long_trip
from unique_records
where row_number = 1 
and EXTRACT(EPOCH FROM dropoff_datetime - pickup_datetime) > 0
and trip_distance / (EXTRACT(EPOCH FROM dropoff_datetime - pickup_datetime) / 3600) <= 300