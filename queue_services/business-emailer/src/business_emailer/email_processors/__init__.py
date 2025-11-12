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
"""This module contains all of the Entity Email specific processors.

Processors hold the business logic for how an email is interpreted and sent.
"""
from __future__ import annotations

import base64
from datetime import datetime
from http import HTTPStatus
from pathlib import Path

import requests
from flask import current_app

from business_model.models import Business, Filing
from business_model.utils.legislation_datetime import LegislationDatetime


def get_filing_info(filing_id: str) -> tuple[Filing, dict, dict, str, str]:
    """Get filing info for the email."""
    filing = Filing.find_by_id(filing_id)
    business_json = None
    if filing.business_id:
        business = Business.find_by_internal_id(filing.business_id)
        business_json = business.json()
        business_json["businessName"] = business.legal_name

    # payment date if available otherwise filing date
    leg_tmz_filing_date = LegislationDatetime.format_as_report_string(
        filing.payment_completion_date if filing.payment_completion_date else filing.filing_date)

    leg_tmz_effective_date = LegislationDatetime.format_as_report_string(filing.effective_date)

    return filing, business_json, leg_tmz_filing_date, leg_tmz_effective_date


def get_recipients(option: str, filing_json: dict, token: str | None = None, filing_type: str | None = None) -> str:
    """Get the recipients for the email output."""
    recipients = ""
    filing_type = filing_type if filing_type else "incorporationApplication"
    if filing_json["filing"].get(filing_type):
        recipients = filing_json["filing"][filing_type]["contactPoint"]["email"]
        if option in [Filing.Status.PAID.value, "bn"] and \
            filing_json["filing"]["header"]["name"] == filing_type:
            parties = filing_json["filing"][filing_type].get("parties")
            comp_party_email = None
            for party in parties:
                for role in party["roles"]:
                    if role["roleType"] == "Completing Party" and \
                        (comp_party_email := party["officer"].get("email")):
                        recipients = f"{recipients}, {comp_party_email}"
                        break
    else:
        identifier = filing_json["filing"]["business"]["identifier"]
        if identifier[:2] != "CP":
            # only add recipients if not coop
            recipients = get_recipient_from_auth(identifier, token)

    return recipients


def get_recipient_from_auth(identifier: str, token: str) -> str:
    """Get the recipients for the email output from auth."""
    headers = {
        "Accept": "application/json",
        "Authorization": f"Bearer {token}"
    }

    contact_info = requests.get(
        f'{current_app.config.get("AUTH_URL")}/entities/{identifier}',
        headers=headers
    )
    contacts = contact_info.json()["contacts"]

    if not contacts:
        current_app.logger.error("Queue Error: No email in business (%s) profile to send output to.", identifier, exc_info=True)
        raise Exception

    return contacts[0]["email"]


def get_user_email_from_auth(user_name: str, token: str) -> str:
    """Get user email from auth."""
    user_info = get_user_from_auth(user_name, token)
    contacts = user_info.json()["contacts"]

    if not contacts:
        return user_info.get("email")  # idir user

    return contacts[0]["email"]


def get_user_from_auth(user_name: str, token: str) -> requests.Response:
    """Get user from auth."""
    headers = {
        "Accept": "application/json",
        "Authorization": f"Bearer {token}"
    }

    user_info = requests.get(
        f'{current_app.config.get("AUTH_URL")}/users/{user_name}',
        headers=headers
    )
    return user_info


def get_account_by_affiliated_identifier(identifier: str, token: str):
    """Return the account affiliated to the business."""
    auth_url = current_app.config.get("AUTH_URL")
    url = f"{auth_url}/orgs?affiliation={identifier}"
    headers = {
        "Accept": "application/json",
        "Authorization": f"Bearer {token}"
    }

    res = requests.get(url, headers=headers)
    try:
        return res.json()
    except Exception:
        current_app.logger.error("Failed to get response")
        return None


def get_org_id_for_temp_identifier(identifier, token: str) -> int:
    """Get org id from auth for the specific identifier."""
    account_response = get_account_by_affiliated_identifier(identifier, token)
    orgs = account_response.get("orgs")
    if not orgs or len(orgs) == 0:
        additional_info = ""
        if identifier.startswith("T"):
            additional_info = ("This is likely due to the temp identifier being removed from the account."
                        "It should work on queue retry (with the business identifier).")
        
        current_app.logger.error(f"Queue Error: No account in auth for identifier {identifier}. {additional_info}")
        raise Exception
    return orgs[0].get("id")  # Temp identifer cannot be present in more than one account


def get_entity_dashboard_url(identifier, token: str) -> str:
    """Get my business registry url when temp identifier otherwise entity dashboard url."""
    entity_dashboard_url = None
    if identifier.startswith("T"):
        org_id = get_org_id_for_temp_identifier(identifier, token)
        auth_web_url = current_app.config.get("AUTH_WEB_URL")
        entity_dashboard_url = f"{auth_web_url}account/{org_id}/business"
    else:
        entity_dashboard_url = current_app.config.get("DASHBOARD_URL") + identifier
    return entity_dashboard_url


def substitute_template_parts(template_code: str) -> str:
    """Substitute template parts in main template.

    Template parts are marked by [[partname.html]] in templates.

    This functionality is restricted by:
    - Markup must be exactly [[partname.html]] and have no extra spaces around the file name.
    - Some nesting is supported: earlier templates can include later templates. Hence, the order of
      template parts, below, is important.
    - Do not comment out template parts as they may be replaced anyway!
    """
    template_parts = [
        "amalgamation-out-information",
        "business-dashboard-link",
        "business-dashboard-link-alt",
        "business-info",
        "business-information",
        "consent-letter-information",
        "continuation-application-details",
        "reg-business-info",
        "cra-notice",
        "nr-footer",
        "footer",
        "header",
        "initiative-notice",
        "logo",
        "pdf-notice",
        "divider",
        "8px",
        "16px",
        "20px",
        "24px",
        "whitespace-16px",
        "whitespace-24px",
        "style"
    ]

    # substitute template parts - marked up by [[filename]]
    for template_part in template_parts:
        template_part_code = (Path(f'{current_app.config.get("TEMPLATE_PATH")}/common/{template_part}.html')
                              .read_text(encoding="utf-8"))
        template_code = template_code.replace(f"[[{template_part}.html]]", template_part_code)

    return template_code


def get_jurisdictions(identifier: str, token: str) -> dict:
    """Get jurisdictions call."""
    headers = {
        "Accept": "application/json",
        "Authorization": f"Bearer {token}"
    }

    response = requests.get(
        f'{current_app.config.get("LEGAL_API_URL")}/mras/{identifier}', headers=headers
    )
    if response.status_code != HTTPStatus.OK:
        return None
    try:
        return response.json()
    except Exception:
        current_app.logger.error("Failed to get MRAS response")
        return None


def get_filing_document(business_identifier, filing_id, document_type, token):
    """Get the filing documents."""
    headers = {
        "Accept": "application/pdf",
        "Authorization": f"Bearer {token}"
    }

    document = requests.get(
        f'{current_app.config.get("LEGAL_API_URL")}/businesses/{business_identifier}/filings/{filing_id}'
        f'/documents/{document_type}', headers=headers
    )

    if document.status_code != HTTPStatus.OK:
        current_app.logger.error("Failed to get %s pdf for filing: %s", document_type, filing_id)
        return None
    try:
        filing_pdf_encoded = base64.b64encode(document.content)
        return filing_pdf_encoded
    except Exception:
        current_app.logger.error("Failed to get document response")
        return None
