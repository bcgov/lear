## What happens next
Once the {{ filing_name | lower }} is effective on {{ formatted_effective_datetime }}, you will receive the following documents by email:
{% for attachment in future_attachments_list -%}
- {{ attachment }}
{% endfor %}
