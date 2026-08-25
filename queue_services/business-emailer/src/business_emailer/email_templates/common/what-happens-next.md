## What happens next
Once the {{ what_happens_next_name | lower }} is effective on {{ effective_date_time }}, you will receive the following documents by email:
{% for attachment in future_attachments_list -%}
- {{ attachment }}
{% endfor %}
