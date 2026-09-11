# Your {{ withdrawn_filing_name }} has been successfully withdrawn

---

{% if filing_id -%}
**Business Name:** {{ business_name }}
**Filing Number:** {{ filing_id }}
{% else -%}
[[business-tombstone-basic.md]]
{% endif -%}
**Withdrawal Date and Time:** {{ withdrawal_date_time }}
**Withdrawn Record:** {{ withdrawn_filing_name }}

---

[[attachments.md]]

---

[[business-registry-footer.md]]
