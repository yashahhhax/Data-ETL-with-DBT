{% test custom_speed_limit(model, column_name) %}
    select *
    from {{ model }}
    where {{ column_name }} > 300
{% endtest %}