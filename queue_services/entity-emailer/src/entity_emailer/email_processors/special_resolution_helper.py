# Copyright © 2020 Province of British Columbia
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
"""Common functions relate to Special Resolution."""
import base64
from http import HTTPStatus

import requests
from flask import current_app, request
from legal_api.models import Filing, LegalEntity

from entity_emailer.services.logging import structured_log


def get_completed_pdfs(
    token: str, business: dict, filing: Filing, name_changed: bool, rules_changed=False, memorandum_changed=False
) -> list:
    # pylint: disable=too-many-locals, too-many-branches, too-many-statements, too-many-arguments
    """Get the completed pdfs for the special resolution output."""
    pdfs = []
    attach_order = 1
    headers = {"Accept": "application/pdf", "Authorization": f"Bearer {token}"}

    # specialResolution
    special_resolution = requests.get(
        f'{current_app.config.get("LEGAL_API_URL")}'
        f'/businesses/{business["identifier"]}'
        f"/filings/{filing.id}"
        "?type=specialResolution",
        headers=headers,
    )
    if special_resolution.status_code == HTTPStatus.OK:
        certificate_encoded = base64.b64encode(special_resolution.content)
        pdfs.append(
            {
                "fileName": "Special Resolution.pdf",
                "fileBytes": certificate_encoded.decode("utf-8"),
                "fileUrl": "",
                "attachOrder": attach_order,
            }
        )
        attach_order += 1
    else:
        structured_log(
            request,
            "ERROR",
            f"Failed to get specialResolution pdf for filing: {filing.id}, status code: {special_resolution.status_code}",  # noqa: E501
        )

    # Change of Name
    if name_changed:
        name_change = requests.get(
            f'{current_app.config.get("LEGAL_API_URL")}/businesses/{business["identifier"]}/filings/{filing.id}'
            "?type=certificateOfNameChange",
            headers=headers,
        )

        if name_change.status_code == HTTPStatus.OK:
            certified_name_change_encoded = base64.b64encode(name_change.content)
            pdfs.append(
                {
                    "fileName": "Certificate of Name Change.pdf",
                    "fileBytes": certified_name_change_encoded.decode("utf-8"),
                    "fileUrl": "",
                    "attachOrder": attach_order,
                }
            )
            attach_order += 1
        else:
            structured_log(
                request,
                "ERROR",
                f"Failed to get certificateOfNameChange pdf for filing: {filing.id}, status code: {name_change.status_code}",  # noqa: E501
            )

    # Certified Rules
    if rules_changed:
        rules = requests.get(
            f'{current_app.config.get("LEGAL_API_URL")}/businesses/{business["identifier"]}/filings/{filing.id}'
            "?type=certifiedRules",
            headers=headers,
        )
        if rules.status_code == HTTPStatus.OK:
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

    # Certified Memorandum
    if memorandum_changed:
        memorandum = requests.get(
            f'{current_app.config.get("LEGAL_API_URL")}/businesses/{business["identifier"]}/filings/{filing.id}'
            "?type=certifiedMemorandum",
            headers=headers,
        )
        if memorandum.status_code == HTTPStatus.OK:
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

    return pdfs


def get_paid_pdfs(
    token: str,
    business: dict,
    filing: Filing,
    filing_date_time: str,
    effective_date: str,
) -> list:
    # pylint: disable=too-many-locals, too-many-branches, too-many-statements, too-many-arguments
    """Get the paid pdfs for the special resolution output."""
    pdfs = []
    attach_order = 1
    headers = {"Accept": "application/pdf", "Authorization": f"Bearer {token}"}

    # add filing pdf
    sr_filing_pdf = requests.get(
        f'{current_app.config.get("LEGAL_API_URL")}'
        f'/businesses/{business["identifier"]}'
        f"/filings/{filing.id}"
        "?type=specialResolutionApplication",
        headers=headers,
    )

    if sr_filing_pdf.status_code != HTTPStatus.OK:
        structured_log(request, "ERROR", f"Failed to get pdf for filing: {filing.id}")
    else:
        sr_filing_pdf_encoded = base64.b64encode(sr_filing_pdf.content)
        pdfs.append(
            {
                "fileName": "Special Resolution Application.pdf",
                "fileBytes": sr_filing_pdf_encoded.decode("utf-8"),
                "fileUrl": "",
                "attachOrder": attach_order,
            }
        )
        attach_order += 1

    business_name = business.get("businessName")
    origin_business = LegalEntity.find_by_internal_id(filing.legal_entity_id)

    sr_receipt = requests.post(
        f'{current_app.config.get("PAY_API_URL")}/{filing.payment_token}/receipts',
        json={
            "corpName": business_name,
            "filingDateTime": filing_date_time,
            "effectiveDateTime": effective_date if effective_date != filing_date_time else "",
            "filingIdentifier": str(filing.id),
            "businessNumber": origin_business.tax_id if origin_business and origin_business.tax_id else "",
        },
        headers=headers,
    )

    if sr_receipt.status_code != HTTPStatus.CREATED:
        structured_log(request, "ERROR", f"Failed to get receipt pdf for filing: {filing.id}")
    else:
        receipt_encoded = base64.b64encode(sr_receipt.content)
        pdfs.append(
            {
                "fileName": "Receipt.pdf",
                "fileBytes": receipt_encoded.decode("utf-8"),
                "fileUrl": "",
                "attachOrder": attach_order,
            }
        )
        attach_order += 1

    return pdfs
