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
from flask import current_app, request
from jinja2 import Template
from legal_api.models import Filing, LegalEntity, UserRoles

from entity_emailer.email_processors import (
    get_filing_info,
    get_recipients,
    get_user_email_from_auth,
    substitute_template_parts,
)
from entity_emailer.services.logging import structured_log

FILING_TYPE_CONVERTER = {
    "incorporationApplication": "IA",
    "annualReport": "AR",
    "changeOfDirectors": "COD",
    "changeOfAddress": "COA",
    "alteration": "ALT",
}


def _get_pdfs(
    status: str,
    token: str,
    business: dict,
    filing: Filing,
    filing_date_time: str,
    effective_date: str,
) -> list:
    # pylint: disable=too-many-locals, too-many-branches, too-many-statements, too-many-arguments
    """Get the pdfs for the incorporation output."""
    pdfs = []
    attach_order = 1
    headers = {"Accept": "application/pdf", "Authorization": f"Bearer {token}"}
    entity_type = business.get("legalType", None)

    if status == Filing.Status.PAID.value:
        # add filing pdf
        filing_pdf = requests.get(
            f'{current_app.config.get("LEGAL_API_URL")}/businesses/{business["identifier"]}/filings/{filing.id}',
            headers=headers,
        )
        if filing_pdf.status_code != HTTPStatus.OK:
            structured_log(request, "ERROR", f"Failed to get pdf for filing: {filing.id}")
        else:
            filing_pdf_encoded = base64.b64encode(filing_pdf.content)
            file_name = filing.filing_type[0].upper() + " ".join(re.findall("[a-zA-Z][^A-Z]*", filing.filing_type[1:]))
            if ar_date := filing.filing_json["filing"].get("annualReport", {}).get("annualReportDate"):
                file_name = f"{ar_date[:4]} {file_name}"

            pdfs.append(
                {
                    "fileName": f"{file_name}.pdf",
                    "fileBytes": filing_pdf_encoded.decode("utf-8"),
                    "fileUrl": "",
                    "attachOrder": attach_order,
                }
            )
            attach_order += 1
        # add receipt pdf
        if filing.filing_type == "incorporationApplication":
            corp_name = filing.filing_json["filing"]["incorporationApplication"]["nameRequest"].get(
                "legalName", "Numbered Company"
            )
        else:
            corp_name = business.get("legalName")

        receipt = requests.post(
            f'{current_app.config.get("PAY_API_URL")}/{filing.payment_token}/receipts',
            json={
                "corpName": corp_name,
                "filingDateTime": filing_date_time,
                "effectiveDateTime": effective_date if effective_date != filing_date_time else "",
                "filingIdentifier": str(filing.id),
                "businessNumber": business.get("taxId", ""),
            },
            headers=headers,
        )
        if receipt.status_code != HTTPStatus.CREATED:
            structured_log(request, "ERROR", f"Failed to get receipt pdf for filing: {filing.id}")
        else:
            receipt_encoded = base64.b64encode(receipt.content)
            pdfs.append(
                {
                    "fileName": "Receipt.pdf",
                    "fileBytes": receipt_encoded.decode("utf-8"),
                    "fileUrl": "",
                    "attachOrder": attach_order,
                }
            )
            attach_order += 1
    if status == Filing.Status.COMPLETED.value:
        if entity_type != LegalEntity.EntityTypes.COOP.value:
            # add notice of articles
            noa = requests.get(
                f'{current_app.config.get("LEGAL_API_URL")}/businesses/{business["identifier"]}/filings/{filing.id}'
                "?type=noticeOfArticles",
                headers=headers,
            )
            if noa.status_code != HTTPStatus.OK:
                structured_log(request, "ERROR", f"Failed to get noa pdf for filing: {filing.id}")
            else:
                noa_encoded = base64.b64encode(noa.content)
                pdfs.append(
                    {
                        "fileName": "Notice of Articles.pdf",
                        "fileBytes": noa_encoded.decode("utf-8"),
                        "fileUrl": "",
                        "attachOrder": attach_order,
                    }
                )
                attach_order += 1

        if filing.filing_type == "incorporationApplication":
            # add certificate
            certificate = requests.get(
                f'{current_app.config.get("LEGAL_API_URL")}/businesses/{business["identifier"]}/filings/{filing.id}'
                "?type=certificate",
                headers=headers,
            )
            if certificate.status_code != HTTPStatus.OK:
                structured_log(
                    request,
                    "ERROR",
                    f"Failed to get certificate pdf for filing: {filing.id}",
                )
            else:
                certificate_encoded = base64.b64encode(certificate.content)
                file_name = "Incorporation Certificate.pdf"
                pdfs.append(
                    {
                        "fileName": file_name,
                        "fileBytes": certificate_encoded.decode("utf-8"),
                        "fileUrl": "",
                        "attachOrder": attach_order,
                    }
                )
                attach_order += 1

            if entity_type == LegalEntity.EntityTypes.COOP.value:
                # Add rules
                rules = requests.get(
                    f'{current_app.config.get("LEGAL_API_URL")}/businesses/{business["identifier"]}/filings/{filing.id}'
                    "?type=certifiedRules",
                    headers=headers,
                )
                if rules.status_code != HTTPStatus.OK:
                    structured_log(
                        request,
                        "ERROR",
                        f"Failed to get certifiedRules pdf for filing: {filing.id}",
                    )
                else:
                    certified_rules_encoded = base64.b64encode(rules.content)
                    pdfs.append(
                        {
                            "fileName": "Certified Rules.pdf",
                            "fileBytes": certified_rules_encoded.decode("utf-8"),
                            "fileUrl": "",
                            "attachOrder": attach_order,
                        }
                    )
                    attach_order += 1

                # Add memorandum
                memorandum = requests.get(
                    f'{current_app.config.get("LEGAL_API_URL")}/businesses/{business["identifier"]}/filings/{filing.id}'
                    "?type=certifiedMemorandum",
                    headers=headers,
                )
                if memorandum.status_code != HTTPStatus.OK:
                    structured_log(
                        request,
                        "ERROR",
                        f"Failed to get certifiedMemorandum pdf for filing: {filing.id}",
                    )
                else:
                    certified_memorandum_encoded = base64.b64encode(memorandum.content)
                    pdfs.append(
                        {
                            "fileName": "Certified Memorandum.pdf",
                            "fileBytes": certified_memorandum_encoded.decode("utf-8"),
                            "fileUrl": "",
                            "attachOrder": attach_order,
                        }
                    )
                    attach_order += 1

        if filing.filing_type == "alteration" and get_additional_info(filing).get("nameChange", False):
            # add certificate of name change
            certificate = requests.get(
                f'{current_app.config.get("LEGAL_API_URL")}/businesses/{business["identifier"]}/filings/{filing.id}'
                "?type=certificateOfNameChange",
                headers=headers,
            )
            if certificate.status_code != HTTPStatus.OK:
                structured_log(
                    request,
                    "ERROR",
                    f"Failed to get certificateOfNameChange pdf for filing: {filing.id}",
                )
            else:
                certificate_encoded = base64.b64encode(certificate.content)
                file_name = "Certificate of Name Change.pdf"
                pdfs.append(
                    {
                        "fileName": file_name,
                        "fileBytes": certificate_encoded.decode("utf-8"),
                        "fileUrl": "",
                        "attachOrder": attach_order,
                    }
                )
                attach_order += 1

    return pdfs


def process(  # pylint: disable=too-many-locals, too-many-statements, too-many-branches
    email_info: dict, token: str
) -> dict:
    """Build the email for Business Number notification."""
    structured_log(request, "DEBUG", f"filing_notification: {email_info}")
    # get template and fill in parts
    filing_type, status = email_info["type"], email_info["option"]
    # get template vars from filing
    filing, business, leg_tmz_filing_date, leg_tmz_effective_date = get_filing_info(email_info["filingId"])
    if filing_type == "incorporationApplication" and status == Filing.Status.PAID.value:
        business = (filing.json)["filing"]["incorporationApplication"]["nameRequest"]
        business["identifier"] = filing.temp_reg

    entity_type = business.get("legalType")
    filing_name = filing.filing_type[0].upper() + " ".join(re.findall("[a-zA-Z][^A-Z]*", filing.filing_type[1:]))

    template = Path(
        f'{current_app.config.get("TEMPLATE_PATH")}/BC-{FILING_TYPE_CONVERTER[filing_type]}-{status}.html'
    ).read_text()
    filled_template = substitute_template_parts(template)
    # render template with vars
    numbered_description = LegalEntity.BUSINESSES.get(entity_type, {}).get("numberedDescription")
    jnja_template = Template(filled_template, autoescape=True)
    filing_data = (filing.json)["filing"][f"{filing_type}"]
    html_out = jnja_template.render(
        business=business,
        filing=filing_data,
        filing_status=status,
        header=(filing.json)["filing"]["header"],
        filing_date_time=leg_tmz_filing_date,
        effective_date_time=leg_tmz_effective_date,
        entity_dashboard_url=current_app.config.get("DASHBOARD_URL") + business.get("identifier", ""),
        email_header=filing_name.upper(),
        filing_type=filing_type,
        numbered_description=numbered_description,
        additional_info=get_additional_info(filing),
    )

    # get attachments
    pdfs = _get_pdfs(status, token, business, filing, leg_tmz_filing_date, leg_tmz_effective_date)

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
    if status == Filing.Status.PAID.value:
        if filing_type == "incorporationApplication":
            subject = "Confirmation of Filing from the Business Registry"
        elif filing_type in ["changeOfAddress", "changeOfDirectors"]:
            address_director = [x for x in ["Address", "Director"] if x in filing_type][0]
            subject = f"Confirmation of {address_director} Change"
        elif filing_type == "annualReport":
            subject = "Confirmation of Annual Report"
        elif filing_type == "alteration":
            subject = "Confirmation of Alteration from the Business Registry"

    elif status == Filing.Status.COMPLETED.value:
        if filing_type == "incorporationApplication":
            subject = "Incorporation Documents from the Business Registry"
        elif filing_type in ["changeOfAddress", "changeOfDirectors", "alteration"]:
            subject = "Notice of Articles"

    if not subject:  # fallback case - should never happen
        subject = "Notification from the BC Business Registry"

    if filing.filing_type == "incorporationApplication":
        business_name = filing.filing_json["filing"]["incorporationApplication"]["nameRequest"].get(
            "businessName", None
        )
    else:
        business_name = business.get("businessName", None)

    subject = f"{business_name} - {subject}" if business_name else subject

    return {
        "recipients": recipients,
        "requestBy": "BCRegistries@gov.bc.ca",
        "content": {"subject": subject, "body": f"{html_out}", "attachments": pdfs},
    }


def get_additional_info(filing: Filing) -> dict:
    """Populate any additional info required for a filing type."""
    additional_info = {}
    if filing.filing_type == "alteration":
        meta_data_alteration = filing.meta_data.get("alteration", {}) if filing.meta_data else {}
        additional_info["nameChange"] = "toLegalName" in meta_data_alteration

    return additional_info
