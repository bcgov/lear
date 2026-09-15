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
from business_emailer.email_processors.util import NOT_AVAILABLE, get_legal_type_key
from business_model.models import Business, Filing, PartyRole


def _get_business_tombstone_context(business: Business, business_number: str) -> dict:
    """Return the values required by the shared business tombstone."""
    business_data = business.json()
    legal_type_key = get_legal_type_key(business.legal_type)
    return {
        "business_name": business_data.get("businessName") or business_data.get("legalName") or NOT_AVAILABLE,
        "business_identifier": business.identifier,
        "business_number": business_number,
        "number_description": "Registration" if legal_type_key == "FIRM" else "Incorporation",
    }


def process(email_msg: dict) -> dict:
    """Build the email for Business Number notification."""
    current_app.logger.debug("bn notification: %s", email_msg)

    # get template and fill in parts
    template = Path(f'{current_app.config.get("TEMPLATE_PATH")}/bnGenerated.md').read_text()
    filled_template = substitute_template_parts(template, "md")

    # get filing and business json
    business = Business.find_by_identifier(email_msg["identifier"])

    # get filings by types. There will be only one of the listed filing types at once
    filings = Filing.get_filings_by_types(business.id, ["amalgamationApplication", "continuationIn",
                                                        "incorporationApplication", "registration"])
    filing = filings[0]
    business_number = business.tax_id.replace("BC", " BC")

    jinja_template = Template(filled_template, autoescape=True)
    body = jinja_template.render(
        **_get_business_tombstone_context(business, business_number),
        entity_dashboard_url=current_app.config.get("DASHBOARD_URL") + business.identifier,
    )

    # get recipients
    recipients = get_recipients(email_msg["option"], filing.filing_json, filing_type=filing.filing_type)
    return {
        "recipients": recipients,
        "requestBy": "BCRegistries@gov.bc.ca",
        "content": {
            "subject": f"{business.legal_name} - Business Number Information",
            "body": body,
            "attachments": []
        }
    }


def process_bn_move(email_msg: dict, token: str) -> dict:
    """Build the email for Business Number move notification."""
    current_app.logger.debug("bn move notification: %s", email_msg)

    # get template and fill in parts
    template = Path(f'{current_app.config.get("TEMPLATE_PATH")}/bnMove.md').read_text()
    filled_template = substitute_template_parts(template, "md")

    # get filing and business json
    business = Business.find_by_identifier(email_msg["identifier"])

    old_bn = email_msg["oldBn"].replace("BC", " BC")
    new_bn = email_msg["newBn"].replace("BC", " BC")

    jinja_template = Template(filled_template, autoescape=True)
    body = jinja_template.render(
        **_get_business_tombstone_context(business, new_bn),
        entity_dashboard_url=current_app.config.get("DASHBOARD_URL") + business.identifier,
        old_bn=old_bn,
        new_bn=new_bn,
    )

    recipients = []
    recipients.append(get_recipient_from_auth(business.identifier, token))

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
            "body": body,
            "attachments": []
        }
    }
