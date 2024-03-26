# Copyright © 2024 Province of British Columbia
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
"""Email processing rules and actions for Amalgamation notifications."""
from __future__ import annotations

import base64
import re
from http import HTTPStatus
from pathlib import Path

import requests
from entity_queue_common.service_utils import logger
from flask import current_app
from jinja2 import Template
from legal_api.models import AmalgamatingBusiness, Amalgamation, Filing, LegalEntity

from entity_emailer.email_processors import get_filing_info, get_recipients, substitute_template_parts


def _get_pdfs(
    status: str,
    token: str,
    business: dict,
    filing: Filing,
    filing_date_time: str,
    effective_date: str,
    amalgamation_application_name: str,
) -> list:
    # pylint: disable=too-many-locals, too-many-branches, too-many-statements, too-many-arguments
    """Get the outputs for the amalgamation notification."""
    pdfs = []
    attach_order = 1
    headers = {"Accept": "application/pdf", "Authorization": f"Bearer {token}"}

    if status == Filing.Status.PAID.value:
        # add filing pdf
        filing_pdf = requests.get(
            f'{current_app.config.get("LEGAL_API_URL")}/businesses/{business["identifier"]}/filings/{filing.id}',
            headers=headers,
        )
        if filing_pdf.status_code != HTTPStatus.OK:
            logger.error("Failed to get pdf for filing: %s", filing.id)
        else:
            filing_pdf_encoded = base64.b64encode(filing_pdf.content)
            pdfs.append(
                {
                    "fileName": f"{amalgamation_application_name}.pdf",
                    "fileBytes": filing_pdf_encoded.decode("utf-8"),
                    "fileUrl": "",
                    "attachOrder": attach_order,
                }
            )
            attach_order += 1

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
            logger.error("Failed to get receipt pdf for filing: %s", filing.id)
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
    elif status == Filing.Status.COMPLETED.value:
        # add certificate of amalgamation
        certificate = requests.get(
            f'{current_app.config.get("LEGAL_API_URL")}/businesses/{business["identifier"]}/filings/{filing.id}'
            "?type=certificateOfAmalgamation",
            headers=headers,
        )
        if certificate.status_code != HTTPStatus.OK:
            logger.error("Failed to get corrected registration statement pdf for filing: %s", filing.id)
        else:
            certificate_encoded = base64.b64encode(certificate.content)
            pdfs.append(
                {
                    "fileName": "Certificate Of Amalgamation.pdf",
                    "fileBytes": certificate_encoded.decode("utf-8"),
                    "fileUrl": "",
                    "attachOrder": attach_order,
                }
            )
            attach_order += 1
        # add notice of articles
        noa = requests.get(
            f'{current_app.config.get("LEGAL_API_URL")}/businesses/{business["identifier"]}/filings/{filing.id}'
            "?type=noticeOfArticles",
            headers=headers,
        )
        if noa.status_code != HTTPStatus.OK:
            logger.error("Failed to get noa pdf for filing: %s", filing.id)
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
    return pdfs


def process(email_info: dict, token: str) -> dict:  # pylint: disable=too-many-locals, , too-many-branches
    """Build the email for Amalgamation notification."""
    logger.debug("filing_notification: %s", email_info)
    amalgamation_application_names = {
        Amalgamation.AmalgamationTypes.regular.name: "Amalgamation Application (Regular)",
        Amalgamation.AmalgamationTypes.vertical.name: "Amalgamation Application Short-form (Vertical)",
        Amalgamation.AmalgamationTypes.horizontal.name: "Amalgamation Application Short-form (Horizontal)",
    }
    # get template and fill in parts
    filing_type, status = email_info["type"], email_info["option"]
    # get template vars from filing
    filing, business, leg_tmz_filing_date, leg_tmz_effective_date = get_filing_info(email_info["filingId"])
    filing_name = filing.filing_type[0].upper() + " ".join(re.findall("[a-zA-Z][^A-Z]*", filing.filing_type[1:]))
    filing_data = (filing.json)["filing"][f"{filing_type}"]
    if status == Filing.Status.PAID.value:
        business = filing_data["nameRequest"]
        business["identifier"] = filing.temp_reg

        if filing.filing_sub_type in [
            Amalgamation.AmalgamationTypes.vertical.name,
            Amalgamation.AmalgamationTypes.horizontal.name,
        ]:
            amalgamating_business = next(
                x
                for x in filing_data.get("amalgamatingBusinesses")
                if x["role"] in [AmalgamatingBusiness.Role.holding.name, AmalgamatingBusiness.Role.primary.name]
            )
            primary_or_holding_business = LegalEntity.find_by_identifier(amalgamating_business["identifier"])
            business["legalName"] = primary_or_holding_business.legal_name

    amalgamation_application_name = amalgamation_application_names[filing.filing_sub_type]

    template = Path(f'{current_app.config.get("TEMPLATE_PATH")}/AMALGA-{status}.html').read_text()
    filled_template = substitute_template_parts(template)
    # render template with vars
    legal_type = business.get("legalType")
    numbered_description = LegalEntity.BUSINESSES.get(legal_type, {}).get("numberedDescription")
    jnja_template = Template(filled_template, autoescape=True)

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
        amalgamation_application_name=amalgamation_application_name,
    )

    # get attachments
    pdfs = _get_pdfs(
        status, token, business, filing, leg_tmz_filing_date, leg_tmz_effective_date, amalgamation_application_name
    )

    # get recipients
    recipients = get_recipients(status, filing.filing_json, token, filing_type)
    if not recipients:
        return {}

    # assign subject
    legal_name = business.get("legalName", None)
    if status == Filing.Status.PAID.value:
        subject_prefix = f"{legal_name} - " if legal_name else ""
        subject = f"{subject_prefix}Amalgamation"
    elif status == Filing.Status.COMPLETED.value:
        subject = f"{legal_name} - Confirmation of Amalgamation"

    return {
        "recipients": recipients,
        "requestBy": "BCRegistries@gov.bc.ca",
        "content": {"subject": subject, "body": f"{html_out}", "attachments": pdfs},
    }
