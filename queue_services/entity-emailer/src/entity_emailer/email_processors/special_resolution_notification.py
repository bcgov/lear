# Copyright © 2023 Province of British Columbia
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
"""Email processing rules and actions for Special Resolution notifications."""
from __future__ import annotations

import re
from pathlib import Path

from flask import current_app, request
from jinja2 import Template
from legal_api.models import Filing, UserRoles

from entity_emailer.email_processors import (
    get_filing_info,
    get_recipient_from_auth,
    get_user_email_from_auth,
    substitute_template_parts,
)
from entity_emailer.email_processors.special_resolution_helper import get_completed_pdfs, get_paid_pdfs
from entity_emailer.services.logging import structured_log


def process(email_info: dict, token: str) -> dict:  # pylint: disable=too-many-locals, too-many-branches
    """Build the email for Special Resolution notification."""
    structured_log(request, "DEBUG", f"special_resolution_notification: {email_info}")
    # get template and fill in parts
    filing_type, status = email_info["type"], email_info["option"]
    # get template vars from filing
    filing, business, leg_tmz_filing_date, leg_tmz_effective_date = get_filing_info(email_info["filingId"])
    filing_name = filing.filing_type[0].upper() + " ".join(re.findall("[a-zA-Z][^A-Z]*", filing.filing_type[1:]))

    template = Path(f'{current_app.config.get("TEMPLATE_PATH")}/SR-CP-{status}.html').read_text()
    filled_template = substitute_template_parts(template)
    # render template with vars
    jnja_template = Template(filled_template, autoescape=True)
    filing_data = (filing.json)["filing"][f"{filing_type}"]
    name_changed = filing.filing_json["filing"].get("changeOfName")
    rules_changed = bool(filing.filing_json["filing"].get("alteration", {}).get("rulesFileKey"))
    html_out = jnja_template.render(
        business=business,
        filing=filing_data,
        header=(filing.json)["filing"]["header"],
        filing_date_time=leg_tmz_filing_date,
        effective_date_time=leg_tmz_effective_date,
        entity_dashboard_url=current_app.config.get("DASHBOARD_URL")
        + (filing.json)["filing"]["business"].get("identifier", ""),
        email_header=filing_name.upper(),
        filing_type=filing_type,
        name_changed=name_changed,
        rules_updated=rules_changed,
    )

    # get attachments
    if status == Filing.Status.PAID.value:
        pdfs = get_paid_pdfs(token, business, filing, leg_tmz_filing_date, leg_tmz_effective_date)
    if status == Filing.Status.COMPLETED.value:
        pdfs = get_completed_pdfs(token, business, filing, name_changed, rules_changed)

    # get recipients
    identifier = filing.filing_json["filing"]["business"]["identifier"]
    recipients = []
    recipients.append(get_recipient_from_auth(identifier, token))

    if filing.submitter_roles and UserRoles.staff in filing.submitter_roles:
        # when staff file a dissolution documentOptionalEmail may contain completing party email
        recipients.append(filing.filing_json["filing"]["header"].get("documentOptionalEmail"))
    else:
        recipients.append(get_user_email_from_auth(filing.filing_submitter.username, token))

    recipients = list(set(recipients))
    recipients = ", ".join(filter(None, recipients)).strip()

    # assign subject
    subject = ""
    if status == Filing.Status.PAID.value:
        subject = "Confirmation of Special Resolution from the Business Registry"
    elif status == Filing.Status.COMPLETED.value:
        subject = "Special Resolution Documents from the Business Registry"

    business_name = business.get("businessName", None)
    subject = f"{business_name} - {subject}" if business_name else subject

    return {
        "recipients": recipients,
        "requestBy": "BCRegistries@gov.bc.ca",
        "content": {"subject": subject, "body": f"{html_out}", "attachments": pdfs},
    }
