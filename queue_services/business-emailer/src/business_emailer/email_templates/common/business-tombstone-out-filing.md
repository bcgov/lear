**Business Name:** {{ business_name }}
**{{number_description}} Number:** {{ business_identifier }}
**Business Number:** {{ business_number }}
{% if consent_expiry_date -%}
**Effective Until:** {{ consent_expiry_date }}
{% endif -%}
**New Jurisdiction:** {{ new_jurisdiction }}
{% if out_date and filing_type == 'amalgamationOut' -%}
**Amalgamate Out Effective Date:** {{ out_date }}
{% elif out_date and filing_type == 'continuationOut' -%}
**Continue Out Effective Date:** {{ out_date }}
{% endif %}
