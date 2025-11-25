{% macro generate_schema_name(custom_schema_name, node) -%}
    {%- set default_schema = target.schema -%}
    
    {%- if custom_schema_name is none -%}
        {{ default_schema }}
    {%- elif custom_schema_name == 'analytics' -%}
        {# Force 'analytics' schema for marts to avoid analytics_analytics #}
        analytics
    {%- else -%}
        {# For staging and intermediate, keep the prefix behavior or customize #}
        {{ default_schema }}_{{ custom_schema_name | trim }}
    {%- endif -%}
{%- endmacro %}