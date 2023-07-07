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
from typing import Dict

import requests
from entity_queue_common.service_utils import logger
from flask import current_app
from legal_api.models import Business, Filing


def get_completed_pdfs(
        token: str,
        business: dict,
        filing: Filing,
        name_changed: bool,
        rules_changed=False) -> list:
    # pylint: disable=too-many-locals, too-many-branches, too-many-statements, too-many-arguments
    """Get the completed pdfs for the special resolution output."""
    pdfs = []
    attach_order = 1
    headers = {
        'Accept': 'application/pdf',
        'Authorization': f'Bearer {token}'
    }

    # specialResolution
    special_resolution = requests.get(
        f'{current_app.config.get("LEGAL_API_URL")}'
        f'/businesses/{business["identifier"]}'
        f'/filings/{filing.id}/documents/specialResolution',
        headers=headers
    )
    if special_resolution.status_code == HTTPStatus.OK:
        certificate_encoded = base64.b64encode(special_resolution.content)
        pdfs.append(
            {
                'fileName': 'Special Resolution.pdf',
                'fileBytes': certificate_encoded.decode('utf-8'),
                'fileUrl': '',
                'attachOrder': attach_order
            }
        )
        attach_order += 1
    else:
        logger.error('Failed to get specialResolution pdf for filing: %s, status code: %s',
                     filing.id, special_resolution.status_code)

    # Change of Name
    if name_changed:
        name_change = requests.get(
            f'{current_app.config.get("LEGAL_API_URL")}/businesses/{business["identifier"]}/filings/{filing.id}'
            '?type=certificateOfNameChange',
            headers=headers
            )

        if name_change.status_code == HTTPStatus.OK:
            certified_name_change_encoded = base64.b64encode(name_change.content)
            pdfs.append(
                {
                    'fileName': 'Certificate of Name Change.pdf',
                    'fileBytes': certified_name_change_encoded.decode('utf-8'),
                    'fileUrl': '',
                    'attachOrder': attach_order
                }
            )
            attach_order += 1
        else:
            logger.error('Failed to get certificateOfNameChange pdf for filing: %s, status code: %s',
                         filing.id, name_change.status_code)

    # Certificate Rules
    if rules_changed:
        rules = requests.get(
            f'{current_app.config.get("LEGAL_API_URL")}/businesses/{business["identifier"]}/filings/{filing.id}'
            '?type=certifiedRules',
            headers=headers
        )
        if rules.status_code == HTTPStatus.OK:
            certified_rules_encoded = base64.b64encode(rules.content)
            pdfs.append(
                {
                    'fileName': 'Certificate Rules.pdf',
                    'fileBytes': certified_rules_encoded.decode('utf-8'),
                    'fileUrl': '',
                    'attachOrder': attach_order
                }
            )
            attach_order += 1

    return pdfs


def get_paid_pdfs(
        token: str,
        business: dict,
        filing: Filing,
        filing_date_time: str,
        effective_date: str) -> list:
    # pylint: disable=too-many-locals, too-many-branches, too-many-statements, too-many-arguments
    """Get the paid pdfs for the special resolution output."""
    pdfs = []
    attach_order = 1
    headers = {
        'Accept': 'application/pdf',
        'Authorization': f'Bearer {token}'
    }

    # add filing pdf
    sr_filing_pdf = requests.get(
        f'{current_app.config.get("LEGAL_API_URL")}'
        f'/businesses/{business["identifier"]}'
        f'/filings/{filing.id}/documents/specialResolutionApplication',
        headers=headers
    )
    if sr_filing_pdf.status_code != HTTPStatus.OK:
        logger.error('Failed to get pdf for filing: %s', filing.id)
    else:
        sr_filing_pdf_encoded = base64.b64encode(sr_filing_pdf.content)
        pdfs.append(
            {
                'fileName': 'Special Resolution Application.pdf',
                'fileBytes': sr_filing_pdf_encoded.decode('utf-8'),
                'fileUrl': '',
                'attachOrder': attach_order
            }
        )
        attach_order += 1

    legal_name = business.get('legalName')
    origin_business = Business.find_by_internal_id(filing.business_id)

    sr_receipt = requests.post(
        f'{current_app.config.get("PAY_API_URL")}/{filing.payment_token}/receipts',
        json={
            'corpName': legal_name,
            'filingDateTime': filing_date_time,
            'effectiveDateTime': effective_date if effective_date != filing_date_time else '',
            'filingIdentifier': str(filing.id),
            'businessNumber': origin_business.tax_id if origin_business and origin_business.tax_id else ''
        },
        headers=headers
    )

    if sr_receipt.status_code != HTTPStatus.CREATED:
        logger.error('Failed to get receipt pdf for filing: %s', filing.id)
    else:
        receipt_encoded = base64.b64encode(sr_receipt.content)
        pdfs.append(
            {
                'fileName': 'Receipt.pdf',
                'fileBytes': receipt_encoded.decode('utf-8'),
                'fileUrl': '',
                'attachOrder': attach_order
            }
        )
        attach_order += 1

    return pdfs


def is_special_resolution_correction(legal_type: str, filing: Dict, business: Business, original_filing: Filing):
    """Check whether it is a special resolution correction."""
    corrected_filing_type = filing['correction'].get('correctedFilingType')

    if legal_type != Business.LegalTypes.COOP.value:
        return False
    if corrected_filing_type == 'specialResolution':
        return True
    if corrected_filing_type not in ('specialResolution', 'correction'):
        return False

    # Find the next original filing in the chain of corrections
    filing = original_filing.filing_json['filing']
    original_filing = Filing.find_by_id(original_filing.filing_json['filing']['correction']['correctedFilingId'])
    return is_special_resolution_correction(legal_type, filing, business, original_filing)
