# Copyright © 2019 Province of British Columbia
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
"""Email processing rules and actions for business number notification."""
from __future__ import annotations

from pathlib import Path

from flask import current_app, request
from jinja2 import Template
from legal_api.models import CorpType, Filing, LegalEntity, PartyRole

from entity_emailer.email_processors import get_recipient_from_auth, get_recipients, substitute_template_parts
from entity_emailer.services.logging import structured_log


def process(email_msg: dict) -> dict:
    """Build the email for Business Number notification."""
    structured_log(request, "DEBUG", f"bn notification: {email_msg}")

    # get template and fill in parts
    template = Path(f'{current_app.config.get("TEMPLATE_PATH")}/BC-BN.html').read_text()
    filled_template = substitute_template_parts(template)

    # get filing and business json
    business = LegalEntity.find_by_identifier(email_msg["identifier"])
    filing_type = "incorporationApplication"
    if business.entity_type in [
        LegalEntity.EntityTypes.SOLE_PROP.value,
        LegalEntity.EntityTypes.PARTNERSHIP.value,
    ]:
        filing_type = "registration"
    filing = Filing.get_a_businesses_most_recent_filing_of_a_type(business.id, filing_type)
    corp_type = CorpType.find_by_id(business.entity_type)

    # render template with vars
    jnja_template = Template(filled_template, autoescape=True)
    html_out = jnja_template.render(
        business=business.json(),
        entityDescription=corp_type.full_desc if corp_type else "",
    )

    # get recipients
    recipients = get_recipients(email_msg["option"], filing.filing_json, filing_type=filing_type)
    return {
        "recipients": recipients,
        "requestBy": "BCRegistries@gov.bc.ca",
        "content": {
            "subject": f"{business.business_name} - Business Number Information",
            "body": html_out,
            "attachments": [],
        },
    }


def process_bn_move(email_msg: dict, token: str) -> dict:
    """Build the email for Business Number move notification."""
    structured_log(request, "DEBUG", f"bn move notification: {email_msg}")

    # get template and fill in parts
    template = Path(f'{current_app.config.get("TEMPLATE_PATH")}/BN-MOVE.html').read_text()
    filled_template = substitute_template_parts(template)

    # get filing and business json
    business = LegalEntity.find_by_identifier(email_msg["identifier"])
    corp_type = CorpType.find_by_id(business.entity_type)

    # render template with vars
    jnja_template = Template(filled_template, autoescape=True)
    html_out = jnja_template.render(
        business=business.json(),
        entityDescription=corp_type.full_desc if corp_type else "",
        old_bn=email_msg["data"]["oldBn"],
        new_bn=email_msg["data"]["newBn"],
    )

    recipients = []
    recipients.append(get_recipient_from_auth(business.identifier, token))  # business email

    role = ""
    if business.entity_type == LegalEntity.EntityTypes.SOLE_PROP.value:
        role = PartyRole.RoleTypes.PROPRIETOR.value
    elif business.entity_type == LegalEntity.EntityTypes.PARTNERSHIP.value:
        role = PartyRole.RoleTypes.PARTNER.value

    if role:
        for party_role in PartyRole.get_parties_by_role(business.id, role):
            if not party_role.cessation_date:
                recipients.append(party_role.party.email)

    recipients = list(set(recipients))
    recipients = ", ".join(filter(None, recipients)).strip()

    return {
        "recipients": recipients,
        "requestBy": "BCRegistries@gov.bc.ca",
        "content": {
            "subject": f"{business.business_name} - Business Number Changed",
            "body": html_out,
            "attachments": [],
        },
    }
