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
import re
from http import HTTPStatus
from pathlib import Path

import requests
from flask import current_app

from business_model.models import Amalgamation, Business, Filing
from business_model.utils.legislation_datetime import LegislationDatetime


def get_filing_info(filing_id: str) -> tuple[Filing, dict, dict, str, str]:
    """Get filing info for the email."""
    filing = Filing.find_by_id(filing_id)
    business_json = None
    if filing.business_id:
        business = Business.find_by_internal_id(filing.business_id)
        business_json = business.json()
        if business.legal_type in ("SP", "GP"):
            business_json["businessName"] = business.legal_name  # `legalName` in json would be replaced for firms

    # payment date if available otherwise filing date
    leg_tmz_filing_date = LegislationDatetime.format_as_report_string(
        filing.payment_completion_date if filing.payment_completion_date else filing.filing_date)

    leg_tmz_effective_date = LegislationDatetime.format_as_report_string(filing.effective_date)

    return filing, business_json, leg_tmz_filing_date, leg_tmz_effective_date


def get_party_emails(parties: list[dict], roles: list[str]) -> list[str]:
    """Return the emails for the specified party types."""
    recipients = []
    for party in parties:
        for role in party["roles"]:
            if role["roleType"] in roles and (email := party["officer"].get("email")):
                recipients.append(email)
                break

    return recipients


def get_recipients(option: str, filing_json: dict, token: str | None = None, filing_type: str | None = None) -> str:
    """Get the recipients for the email output."""
    recipients = ""
    identifier = filing_json["filing"]["business"]["identifier"]
    is_coop = identifier.startswith("CP")

    if filing_type and (filing_data := filing_json["filing"].get(filing_type)):
        # add filing contact point email
        recipients = filing_data.get("contactPoint", {}).get("email", "") or ""

        # add relevant party emails
        # FUTURE: after amalg and continuation have completing party removed 'temp_logic' can be removed
        temp_logic = filing_type in ["amalgamationApplication", "continuationIn"] and option in ["PAID", "bn"]
        is_coop_incorp_paid = is_coop and filing_type == "incorporationApplication" and option == "PAID"
        is_valid_filing = filing_type in ["changeOfRegistration", "registration", "correction", "dissolution"]
        if ((temp_logic or is_coop_incorp_paid or is_valid_filing)
            and (parties := filing_data.get("parties"))
            and (party_emails := get_party_emails(parties, ["Completing Party", "Custodian", "Partner", "Proprietor"]))
        ):
            recipients = f"{recipients}, {', '.join(party_emails)}"

    else:
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
    contacts = (contact_info.json()).get("contacts")

    if not contacts:
        current_app.logger.error("Queue Error: No email in business (%s) profile to send output to.", identifier, exc_info=True)
        raise Exception

    return contacts[0]["email"]


def get_user_email_from_auth(user_name: str, token: str) -> str:
    """Get user email from auth."""
    user_info = get_user_from_auth(user_name, token)
    contacts = (user_info.json()).get("contacts")

    if not contacts:
        return user_info.json().get("email")  # idir user
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


def substitute_template_parts(template_code: str, file_type = "html") -> str:
    """Substitute template parts in main template.

    Template parts are marked by [[partname.{file_type}]] in templates.

    This functionality is restricted by:
    - Markup must be exactly [[partname.{file_type}]] and have no extra spaces around the file name.
    - Some nesting is supported: earlier templates can include later templates. Hence, the order of
      template parts, below, is important.
    - Do not comment out template parts as they may be replaced anyway!
    """
    if file_type == "md":
        template_parts = [
            "attachments",
            "business-number",
            "business-registry-footer",
            "business-tombstone",
            "what-happens-next"
        ]
    else:
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
        template_part_code = (Path(f'{current_app.config.get("TEMPLATE_PATH")}/common/{template_part}.{file_type}')
                              .read_text(encoding="utf-8"))
        template_code = template_code.replace(f"[[{template_part}.{file_type}]]", template_part_code)

    return template_code


def get_extra_provincials(response: dict) -> list[str]:
    """Get extra provincials name."""
    extra_provincials = []
    if response:
        jurisdictions = response.get("jurisdictions", [])
        # List of NWPTA jurisdictions
        nwpta_jurisdictions = ["Alberta", "British Columbia", "Manitoba", "Saskatchewan"]
        for jurisdiction in jurisdictions:
            name = jurisdiction.get("name")
            if name and (name in nwpta_jurisdictions):
                extra_provincials.append(name)
        extra_provincials.sort()
    return extra_provincials


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


def get_filing_document(business_identifier, filing_id, document_type, token, regenerate=False):
    """Get the filing documents."""
    headers = {
        "Accept": "application/pdf",
        "Authorization": f"Bearer {token}"
    }

    params = {"regenerate": regenerate}
    document = requests.get(
        f'{current_app.config.get("LEGAL_API_URL")}/businesses/{business_identifier}/filings/{filing_id}'
        f'/documents/{document_type}', headers=headers, params=params
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


def get_filled_template(filing_type: str, is_future_effective_paid: bool):
    """Return the filled email template for the filing type."""
    path = f'{current_app.config.get("TEMPLATE_PATH")}/{filing_type}.md'
    if is_future_effective_paid:
        path = f'{current_app.config.get("TEMPLATE_PATH")}/{filing_type}-future.md'
    template = Path(path).read_text()

    return substitute_template_parts(template, "md")


def get_subject(is_future_effective_paid: bool, business_name: str, legal_type: str, filing_name: str, filing_name_short: str) -> str:
    """Return the subject for the email."""
    if is_future_effective_paid:
        if not business_name or business_name == "Not Available":
            # assume its numbered
            numbered_description = Business.BUSINESSES.get(legal_type, {}).get("numberedDescription")
            return f"{numbered_description} - {filing_name} Filed"

        return f"{business_name} - {filing_name} Filed"

    return f"{business_name} - Successful {filing_name_short}"


def _add_filing_document_pdf(  # noqa: PLR0913
    pdfs: list[dict],
    attach_order: int,
    document_type: str,
    token: str,
    business: dict,
    filing: Filing,
    file_attachment_name: str | None = None,
    regenerate=False
):
    """Add the specified filing document pdf to the pdfs list."""
    # File name
    if not (file_name := file_attachment_name):
        file_name = (document_type[0].upper() + " ".join(re.findall("[a-zA-Z][^A-Z]*", document_type[1:]))).replace(" Of ", " of ")

    if document_type == "annualReport" and (ar_date := filing.filing_json["filing"].get("annualReport", {}).get("annualReportDate")):
        file_name = f"{ar_date[:4]} {file_name}"

    # Get pdf and add it to the list
    filing_pdf_encoded = get_filing_document(business["identifier"], filing.id, document_type, token, regenerate=regenerate)
    if filing_pdf_encoded:
        pdfs.append(
            {
                "fileName": f"{file_name}.pdf",
                "fileBytes": filing_pdf_encoded.decode("utf-8"),
                "fileUrl": "",
                "attachOrder": str(attach_order)
            }
        )
        attach_order += 1

    return attach_order


def _add_receipt_pdf(  # noqa: PLR0913
    pdfs: list[dict],
    attach_order: int,
    token: str,
    business: dict,
    filing: Filing,
    filing_date_time: str,
    effective_date: str
):
    """Add the filing receipt pdf to the pdfs list."""
    headers = {
        "Accept": "application/pdf",
        "Authorization": f"Bearer {token}"
    }
    if not (corp_name := business.get("legalName")):  # pylint: disable=superfluous-parens
        legal_type = business.get("legalType")
        corp_name = Business.BUSINESSES.get(legal_type, {}).get("numberedDescription")

    receipt = requests.post(
        f'{current_app.config.get("PAY_API_URL")}/{filing.payment_token}/receipts',
        json={
            "corpName": corp_name,
            "filingDateTime": filing_date_time,
            "effectiveDateTime": effective_date if effective_date != filing_date_time else "",
            "filingIdentifier": str(filing.id),
            "businessNumber": business.get("taxId", "")
        },
        headers=headers
    )
    if receipt.status_code != HTTPStatus.CREATED:
        current_app.logger.error("Failed to get receipt pdf for filing: %s", filing.id)
    else:
        receipt_encoded = base64.b64encode(receipt.content)
        pdfs.append(
            {
                "fileName": "Receipt.pdf",
                "fileBytes": receipt_encoded.decode("utf-8"),
                "fileUrl": "",
                "attachOrder": str(attach_order)
            }
        )
        return attach_order + 1


def get_pdfs(  # noqa: PLR0913
    token: str,
    business: dict,
    filing: Filing,
    filing_date_time: str,
    effective_date: str,
    extra_pdf_type_list: list[str],
    filing_attachment_name: str | None,
    regenerate=False
) -> list:
    """Get the pdfs for the filing output."""
    pdfs = []
    attach_order = 1
    # add filing application document
    attach_order = _add_filing_document_pdf(pdfs, attach_order, filing.filing_type, token, business, filing, filing_attachment_name, regenerate=regenerate)
    # add extra documents
    for pdf_type in extra_pdf_type_list:
        attach_order = _add_filing_document_pdf(pdfs, attach_order, pdf_type, token, business, filing, regenerate=regenerate)
    # add receipt
    attach_order = _add_receipt_pdf(pdfs, attach_order, token, business, filing, filing_date_time, effective_date)
    return pdfs
