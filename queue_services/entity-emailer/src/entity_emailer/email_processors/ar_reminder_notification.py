# Copyright © 2021 Province of British Columbia
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
"""Email processing actions for annual report reminder notification."""
from __future__ import annotations

from pathlib import Path

from flask import current_app, request
from jinja2 import Template
from legal_api.models import CorpType, LegalEntity

from entity_emailer.email_processors import get_recipient_from_auth, substitute_template_parts
from entity_emailer.services.logging import structured_log


def process(email_msg: dict, token: str, flag_on: bool) -> dict:
    """Build the email for annual report reminder notification."""
    structured_log(request, "DEBUG", f"ar_reminder_notification: {email_msg}")
    ar_fee = email_msg["arFee"]
    ar_year = email_msg["arYear"]
    # get template and fill in parts
    template = Path(f'{current_app.config.get("TEMPLATE_PATH")}/AR-REMINDER.html').read_text()
    filled_template = substitute_template_parts(template)
    business = LegalEntity.find_by_internal_id(email_msg["businessId"])
    corp_type = CorpType.find_by_id(business.entity_type)

    # render template with vars
    jnja_template = Template(filled_template, autoescape=True)
    html_out = jnja_template.render(
        business=business.json(),
        ar_fee=ar_fee,
        ar_year=ar_year,
        entity_type=corp_type.full_desc,
        entity_dashboard_url=current_app.config.get("DASHBOARD_URL") + business.identifier,
        disable_specific_service_provider=flag_on,
    )

    # get recipients
    recipients = get_recipient_from_auth(business.identifier, token)
    subject = f"{business.business_name} {ar_year} Annual Report Reminder"

    return {
        "recipients": recipients,
        "requestBy": "BCRegistries@gov.bc.ca",
        "content": {"subject": subject, "body": f"{html_out}", "attachments": []},
    }
