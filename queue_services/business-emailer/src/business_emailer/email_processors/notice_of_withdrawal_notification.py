# Copyright © 2025 Province of British Columbia
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
"""Email processing rules and actions for Notice of Withdrawal notifications."""
import base64
from http import HTTPStatus
from pathlib import Path

import requests
from flask import current_app
from jinja2 import Template

from business_emailer.email_processors import (
    get_filing_document,
    get_filing_info,
    get_recipient_from_auth,
    substitute_template_parts,
)
from business_emailer.email_processors.util import FILING_TITLE, get_legal_type_key
from business_model.models import Business, Filing


def process(email_info: dict, token: str) -> dict:  # pylint: disable=too-many-locals
    """Build the email for Notice of Withdrawal notification."""
    current_app.logger.debug("notice_of_withdrawal_notification: %s", email_info)
    filing_type = email_info["type"]

    # get template variables from filing
    filing, business, leg_tmz_filing_date, leg_tmz_effective_date = get_filing_info(email_info["filingId"])
    withdrawn_filing = Filing.find_by_id(filing.withdrawn_filing_id)
    if not business:  # Temporary business
        # Business name comes from the nameRequest (NR name, or the primary/holding business name for
        # short-form amalgamations, which the UI copies into the nameRequest).
        business = (withdrawn_filing.json)["filing"][withdrawn_filing.filing_type]["nameRequest"]
        business["identifier"] = withdrawn_filing.temp_reg

    legal_type = business.get("legalType")
    identifier = business.get("identifier")
    is_temp = identifier.startswith("T")

    # display company name for existing businesses and temp businesses
    company_name = (
        business.get("legalName")
        or Business.BUSINESSES.get(legal_type, {}).get("numberedDescription")
        # fall back default value
        or "Unknown Company"
    )
    # record to be withdrawn --> withdrawn filing display name
    withdrawn_filing_display_name = FILING_TITLE.get(withdrawn_filing.filing_type)
    if isinstance(withdrawn_filing_display_name, dict):
        withdrawn_filing_display_name = withdrawn_filing_display_name.get(withdrawn_filing.filing_sub_type)

    # show the withdrawn filing ID (instead of the incorporation number) when the withdrawn record
    # is a new business filing (IA, Amalgamation or Continuation In)
    filing_id = None
    if is_temp:
        filing_id = (filing.json)["filing"][filing_type]["filingId"]

    business_number = None
    if not is_temp and len(business.get("taxId") or "") > 9:  # noqa: PLR2004
        # Only show if bn15 is saved, format for ux
        business_number = business["taxId"].replace("BC", " BC")

    # get attachments
    pdfs = _get_pdfs(token, business, filing, leg_tmz_filing_date, leg_tmz_effective_date)
    attachments_list = [pdf["fileName"].replace(".pdf", "") for pdf in pdfs]

    # get template and fill in parts
    template = Path(
        f'{current_app.config.get("TEMPLATE_PATH")}/noticeOfWithdrawal.md'
    ).read_text(encoding="utf-8")
    filled_template = substitute_template_parts(template, "md")
    # render template with vars
    jnja_template = Template(filled_template, autoescape=True)
    body = jnja_template.render(
        attachments_list=attachments_list,
        business_identifier=identifier,
        business_name=company_name,
        business_number=business_number,
        entity_dashboard_url=current_app.config.get("DASHBOARD_URL") + identifier,
        filing_id=filing_id,
        number_description="Registration" if get_legal_type_key(legal_type) == "FIRM" else "Incorporation",
        withdrawal_date_time=leg_tmz_effective_date,
        withdrawn_filing_name=withdrawn_filing_display_name
    )

    # get recipients
    recipients = _get_contacts(identifier, token, withdrawn_filing)
    recipients = list(set(recipients))
    recipients = ", ".join(filter(None, recipients)).strip()

    # assign subject
    subject = "Notice of Withdrawal filed Successfully"
    legal_name = company_name
    legal_name = "Numbered Company" if legal_name.startswith(identifier) else legal_name
    subject = f"{legal_name} - {subject}"

    return {
        "recipients": recipients,
        "requestBy": "BCRegistries@gov.bc.ca",
        "content": {
            "subject": subject,
            "body": body,
            "attachments": pdfs
        }
    }


def _get_pdfs(
    token: str,
    business: dict,
    filing: Filing,
    filing_date_time: str,
    effective_date: str) -> list:
    """Get the PDFs for the Notice of Withdrawal output."""
    pdfs = []
    attach_order = 1
    headers = {
        "Accept": "application/pdf",
        "Authorization": f"Bearer {token}"
    }

    # add filing PDF
    filing_pdf_type = "noticeOfWithdrawal"
    filing_pdf_encoded = get_filing_document(business["identifier"], filing.id, filing_pdf_type, token)
    if filing_pdf_encoded:
        pdfs.append(
            {
                "fileName": "Notice of Withdrawal.pdf",
                "fileBytes": filing_pdf_encoded.decode("utf-8"),
                "fileUrl": "",
                "attachOrder": str(attach_order)
            }
        )
        attach_order += 1

    # add receipt PDF
    corp_name = business.get("legalName")
    if business.get("identifier").startswith("T"):
        business_data = None
    else:
        business_data = Business.find_by_internal_id(filing.business_id)
    receipt = requests.post(
        f'{current_app.config.get("PAY_API_URL")}/{filing.payment_token}/receipts',
        json={
            "corpName": corp_name,
            "filingDateTime": filing_date_time,
            "effectiveDateTime": effective_date if effective_date else "",
            "filingIdentifier": str(filing.id),
            "businessNumber": business_data.tax_id if business_data and business_data.tax_id else ""
        }, headers=headers)

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
            })
        attach_order += 1
    return pdfs


def _get_contacts(identifier, token, withdrawn_filing):
    recipients = []
    if identifier.startswith("T"):
        # get from withdrawn filing (FE new business filing)
        filing_type = withdrawn_filing.filing_type
        recipients.append(withdrawn_filing.filing_json["filing"][filing_type]["contactPoint"]["email"])

        for party in withdrawn_filing.filing_json["filing"][filing_type]["parties"]:
            for role in party["roles"]:
                if role["roleType"] == "Completing Party":
                    recipients.append(party["officer"].get("email"))
                    break
    else:
        recipients.append(get_recipient_from_auth(identifier, token))

    return recipients
