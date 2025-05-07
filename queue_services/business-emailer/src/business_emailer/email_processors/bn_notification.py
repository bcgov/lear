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

from flask import current_app
from jinja2 import Template

from business_emailer.email_processors import get_recipient_from_auth, get_recipients, substitute_template_parts
from business_model.models import Business, CorpType, Filing, PartyRole


def process(email_msg: dict) -> dict:
    """Build the email for Business Number notification."""
    current_app.logger.debug("bn notification: %s", email_msg)

    # get template and fill in parts
    template = Path(f'{current_app.config.get("TEMPLATE_PATH")}/BC-BN.html').read_text()
    filled_template = substitute_template_parts(template)

    # get filing and business json
    business = Business.find_by_identifier(email_msg["identifier"])

    # get filings by types. There will be only one of the listed filing types at once
    filings = Filing.get_filings_by_types(business.id, ["amalgamationApplication", "continuationIn",
                                                        "incorporationApplication", "registration"])
    filing = filings[0]
    corp_type = CorpType.find_by_id(business.legal_type)

    # render template with vars
    jnja_template = Template(filled_template, autoescape=True)
    html_out = jnja_template.render(
        business=business.json(),
        entityDescription=corp_type.full_desc if corp_type else ""
    )

    # get recipients
    recipients = get_recipients(email_msg["option"], filing.filing_json, filing_type=filing.filing_type)
    return {
        "recipients": recipients,
        "requestBy": "BCRegistries@gov.bc.ca",
        "content": {
            "subject": f"{business.legal_name} - Business Number Information",
            "body": html_out,
            "attachments": []
        }
    }


def process_bn_move(email_msg: dict, token: str) -> dict:
    """Build the email for Business Number move notification."""
    current_app.logger.debug("bn move notification: %s", email_msg)

    # get template and fill in parts
    template = Path(f'{current_app.config.get("TEMPLATE_PATH")}/BN-MOVE.html').read_text()
    filled_template = substitute_template_parts(template)

    # get filing and business json
    business = Business.find_by_identifier(email_msg["identifier"])
    corp_type = CorpType.find_by_id(business.legal_type)

    # render template with vars
    jnja_template = Template(filled_template, autoescape=True)
    html_out = jnja_template.render(
        business=business.json(),
        entityDescription=corp_type.full_desc if corp_type else "",
        old_bn=email_msg["oldBn"],
        new_bn=email_msg["newBn"]
    )

    recipients = []
    recipients.append(get_recipient_from_auth(business.identifier, token))  # business email

    role = ""
    if business.legal_type == Business.LegalTypes.SOLE_PROP.value:
        role = PartyRole.RoleTypes.PROPRIETOR.value
    elif business.legal_type == Business.LegalTypes.PARTNERSHIP.value:
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
            "subject": f"{business.legal_name} - Business Number Changed",
            "body": html_out,
            "attachments": []
        }
    }
