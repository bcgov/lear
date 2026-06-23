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
"""Email processing rules and actions for Incorporation Application notifications."""
from __future__ import annotations

import base64
import re
from http import HTTPStatus
from pathlib import Path

import requests
from flask import current_app
from jinja2 import Template

from business_emailer.email_processors import (
    get_entity_dashboard_url,
    get_filing_document,
    get_filing_info,
    get_filled_template,
    get_recipients,
    get_subject,
    get_user_email_from_auth,
    substitute_template_parts,
)
from business_model.models import Business, Filing, UserRoles

FILING_TYPE_CONVERTER = {
    "incorporationApplication": "IA",
    "annualReport": "AR",
    "changeOfDirectors": "COD",
    "changeOfAddress": "COA",
    "alteration": "ALT"
}

FILING_TITLE = {
    "alteration": "Alteration",
    "annualReport": "Annual Report",
    "changeOfDirectors": "Change of Directors",
    "changeOfAddress": "Change of Address",
    "incorporationApplication": "Incorporation Application",
}

FUTURE_ATTACHMENTS = {
    "incorporationApplication": {
        "CORP": ["Incorporation Application","Notice of Articles","Certificate of Incorporation","Receipt"],
        "CP": ["Incorporation Application","Certificate of Incorporation","Certified Rules","Memorandum","Receipt"],
    }
}


def _add_filing_document_pdf(  # noqa: PLR0913
    pdfs: list[dict],
    attach_order: int,
    document_type: str,
    token: str,
    business: dict,
    filing: Filing,
):
    """Add the specified filing document pdf to the pdfs list."""
    # File name
    file_name = (document_type[0].upper() + " ".join(re.findall("[a-zA-Z][^A-Z]*", document_type[1:]))).replace(" Of ", " of ")
    if document_type == "annualReport" and (ar_date := filing.filing_json["filing"].get("annualReport", {}).get("annualReportDate")):
        file_name = f"{ar_date[:4]} {file_name}"

    # Get pdf and add it to the list
    filing_pdf_encoded = get_filing_document(business["identifier"], filing.id, document_type, token)
    if filing_pdf_encoded:
        pdfs.append(
            {
                "fileName": f"{file_name}.pdf",
                "fileBytes": filing_pdf_encoded.decode("utf-8"),
                "fileUrl": "",
                "attachOrder": str(attach_order)
            }
        )
        return attach_order + 1


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


def _get_pdfs(  # noqa: PLR0913
    status: str,
    token: str,
    business: dict,
    filing: Filing,
    filing_date_time: str,
    effective_date: str
) -> list:
    """Get the pdfs for the incorporation output."""
    pdfs = []
    attach_order = 1
    legal_type = business.get("legalType")

    noa_pdf_type = "noticeOfArticles"
    incorp_certificate_pdf_type = "certificateOfIncorporation"
    memorandum_pdf_type = "memorandum"
    rules_pdf_type = "certifiedRules"
    name_change_certificate_pdf_type = "certificateOfNameChange"
    
    # FUTURE: rework branch logic once other filings are sending the updated emails
    if filing.filing_type in ["incorporationApplication"]:
        # add filing application document
        attach_order = _add_filing_document_pdf(pdfs, attach_order, filing.filing_type, token, business, filing)

        if status == Filing.Status.COMPLETED.value:
            if legal_type == Business.LegalTypes.COOP.value:
                # add cert, memorandum and rules
                attach_order = _add_filing_document_pdf(pdfs, attach_order, incorp_certificate_pdf_type, token, business, filing)
                attach_order = _add_filing_document_pdf(pdfs, attach_order, rules_pdf_type, token, business, filing)
                attach_order = _add_filing_document_pdf(pdfs, attach_order, memorandum_pdf_type, token, business, filing)
            else:
                # add noa and cert
                attach_order = _add_filing_document_pdf(pdfs, attach_order, noa_pdf_type, token, business, filing)
                attach_order = _add_filing_document_pdf(pdfs, attach_order, incorp_certificate_pdf_type, token, business, filing)

        # add receipt
        attach_order = _add_receipt_pdf(pdfs, attach_order, token, business, filing, filing_date_time, effective_date)

    elif status == Filing.Status.PAID.value:
        # add filing pdf
        attach_order = _add_filing_document_pdf(pdfs, attach_order, filing.filing_type, token, business, filing)
        # add receipt pdf
        attach_order = _add_receipt_pdf(pdfs, attach_order, token, business, filing, filing_date_time, effective_date)

    elif status == Filing.Status.COMPLETED.value:
        if legal_type != Business.LegalTypes.COOP.value:
            # add notice of articles
            attach_order = _add_filing_document_pdf(pdfs, attach_order, noa_pdf_type, token, business, filing)

        if filing.filing_type == "alteration" and get_additional_info(filing).get("nameChange", False):
            # add certificate of name change
            attach_order = _add_filing_document_pdf(pdfs, attach_order, name_change_certificate_pdf_type, token, business, filing)

    return pdfs


def process(email_info: dict, token: str) -> dict:  # noqa: PLR0915, PLR0912 ; will get resolved once other filings are updated and logic is condensed
    """Build the email for Business Number notification."""
    current_app.logger.debug("filing_notification: %s", email_info)
    filing_type, status = email_info["type"], email_info["option"]
    # get template vars from filing
    filing, business, leg_tmz_filing_date, leg_tmz_effective_date = get_filing_info(email_info["filingId"])
    
    updated_filings = ["incorporationApplication"]
    if filing_type in updated_filings and status == Filing.Status.PAID.value and not filing.is_future_effective:
        # We no longer send an email for this case
        return

    filing_data = (filing.json)["filing"][filing_type]
    if not business:  # incorporationApplication (if filing status PAID):
        business = filing_data["nameRequest"]
        business["identifier"] = filing.temp_reg

    legal_type = business.get("legalType")
    filing_name = filing.filing_type[0].upper() + " ".join(re.findall("[a-zA-Z][^A-Z]*", filing.filing_type[1:]))
    filing_doc_title = FILING_TITLE[filing_type]
    show_effective_date = filing.is_future_effective
    is_future_effective_paid = filing.is_future_effective and status == Filing.Status.PAID.value
    business_name = business.get("legalName") or "Not Available"
    business_identifier = business.get("identifier")
    business_number = None
    filing_name_short = ""
    future_attachments_list = []
    dashboard_url = get_entity_dashboard_url(business_identifier, token)

    if len(business.get("taxId", "")) > 9:  # noqa: PLR2004
        # Only show if bn15 is saved and format for ux
        business_number = business["taxId"].replace("BC", " BC")

    # get template and fill in parts
    if filing_type == "incorporationApplication":
        dashboard_url = current_app.config.get("DASHBOARD_URL") + business_identifier
        filing_name_short = "Incorporation"
        filled_template = get_filled_template(filing.filing_type, is_future_effective_paid)
        if is_future_effective_paid:
            business_identifier = "Not Available"
            if legal_type == Business.LegalTypes.COOP.value:
                future_attachments_list = FUTURE_ATTACHMENTS["incorporationApplication"]["CP"]
            else:
                future_attachments_list = FUTURE_ATTACHMENTS["incorporationApplication"]["CORP"]
            
        if not business_number and legal_type != Business.LegalTypes.COOP.value:
            business_number = "Not Available"

    else:
        template = Path(
            f'{current_app.config.get("TEMPLATE_PATH")}/BC-{FILING_TYPE_CONVERTER[filing_type]}-{status}.html'
        ).read_text()
        filled_template = substitute_template_parts(template)

    # get attachments
    pdfs = _get_pdfs(status, token, business, filing, leg_tmz_filing_date, leg_tmz_effective_date)
    # render template with vars
    attachments_list = [pdf["fileName"].replace(".pdf", "") for pdf in pdfs]
    jnja_template: Template = Template(filled_template, autoescape=True)
    rendered_template = jnja_template.render(
        business=business,
        filing=filing_data,
        filing_status=status,
        header=(filing.json)["filing"]["header"],
        filing_date_time=leg_tmz_filing_date,
        effective_date_time=leg_tmz_effective_date,
        entity_dashboard_url=dashboard_url,
        filing_type=filing_type,
        additional_info=get_additional_info(filing),
        attachments_list=attachments_list,
        business_name=business_name,
        business_identifier=business_identifier,
        business_number=business_number,
        filing_doc_title=filing_doc_title,
        filing_name=filing_name,
        filing_name_short=filing_name_short,
        future_attachments_list=future_attachments_list,
        office_name="Registered Office",
        show_effective_date=show_effective_date,
    )

    # get recipients
    recipients = get_recipients(status, filing.filing_json, token)
    if filing_type == "alteration":
        if filing.submitter_roles and UserRoles.staff in filing.submitter_roles:
            # when staff do filing documentOptionalEmail may contain completing party email
            optional_email = filing.filing_json["filing"]["header"].get("documentOptionalEmail")
            if optional_email:
                recipients = f"{recipients}, {optional_email}"
        else:
            user_email = get_user_email_from_auth(filing.filing_submitter.username, token)
            recipients = f"{recipients}, {user_email}"

    if not recipients:
        return {}

    # assign subject
    if filing_type == "incorporationApplication":
        # FUTURE - all filings will follow this logic
        subject = get_subject(is_future_effective_paid, business_name, legal_type, filing_name, filing_name_short)

    else:
        if status == Filing.Status.PAID.value:
            if filing_type in ["changeOfAddress", "changeOfDirectors"]:
                address_director = next(x for x in ["Address", "Director"] if x in filing_type)
                subject = f"Confirmation of {address_director} Change"
            elif filing_type == "annualReport":
                subject = "Confirmation of Annual Report"
            elif filing_type == "alteration":
                subject = "Confirmation of Alteration from the Business Registry"

        elif status == Filing.Status.COMPLETED.value and filing_type in ["changeOfAddress", "changeOfDirectors", "alteration"]:
            subject = "Notice of Articles"

        if not subject:  # fallback case - should never happen
            subject = "Notification from the BC Business Registry"

        legal_name = business.get("legalName", None)

        subject = f"{legal_name} - {subject}" if legal_name else subject

    return {
        "recipients": recipients,
        "requestBy": "BCRegistries@gov.bc.ca",
        "content": {
            "subject": subject,
            "body": rendered_template,
            "attachments": pdfs
        }
    }


def get_additional_info(filing: Filing) -> dict:
    """Populate any additional info required for a filing type."""
    additional_info = {}
    if filing.filing_type == "alteration":
        meta_data_alteration = filing.meta_data.get("alteration", {}) if filing.meta_data else {}
        additional_info["nameChange"] = "toLegalName" in meta_data_alteration

    return additional_info
