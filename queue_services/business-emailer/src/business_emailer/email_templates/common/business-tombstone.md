**Business Name:** {{ business_name }}
**{{number_description}} Number:** {{ business_identifier }}
{% if business_number -%}
**Business Number:** {{ business_number }}
{% endif -%}
**Filed Date and Time:** {{ filing_date_time }}
{% if show_effective_date -%}
**Effective Date and Time:** {{ effective_date_time }}
{% endif %}
