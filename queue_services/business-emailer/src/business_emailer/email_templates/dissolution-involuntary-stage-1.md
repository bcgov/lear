# Your business is in the process of being {{ action }} for {{ reason_title }}

---

[[business-tombstone-basic.md]]

---

## Attention

Your business is in the process of being {{ action }} because {{ reason_description }}.

{% if extra_provincials_display -%}
Our records indicate your business is registered in {{ extra_provincials_display }} as an extraprovincial company. If your business is {{ action }}, its registration as an extraprovincial company in {{ extra_provincials_display }} will automatically be cancelled as well.

{% endif -%}
See the attached document for more information.

---

## Next Steps

Log into your [BC Business Registry account]({{ entity_dashboard_url }}) and {{ next_step_action }}.

If you need more time, you can request a delay of {{ delay_type }} from your account.

---

## Attachments

The following document is attached to this email:

- {{ attachment_name }}

---

[[business-registry-footer.md]]
