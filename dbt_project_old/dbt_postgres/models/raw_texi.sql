-- models/raw_texi.sql

{{ config(materialized='table') }}

SELECT *
FROM {{ source('Texi_data', 'Texi_data') }}