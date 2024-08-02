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
from entity_queue_common.service_utils import logger
from flask import current_app
from legal_api.models import Business, Filing

from entity_emailer.email_processors import get_filing_document


def get_completed_pdfs(
        token: str,
        business: dict,
        filing: Filing,
        name_changed: bool,
        rules_changed=False,
        memorandum_changed=False) -> list:
    # pylint: disable=too-many-locals, too-many-branches, too-many-statements, too-many-arguments
    """Get the completed pdfs for the special resolution output."""
    pdfs = []
    attach_order = 1

    # specialResolution
    special_resolution_pdf_type = 'specialResolution'
    special_resolution_encoded = get_filing_document(business['identifier'], filing.id,
                                                     special_resolution_pdf_type, token)
    if special_resolution_encoded:
        pdfs.append(
            {
                'fileName': 'Special Resolution.pdf',
                'fileBytes': special_resolution_encoded.decode('utf-8'),
                'fileUrl': '',
                'attachOrder': str(attach_order)
            }
        )
        attach_order += 1

    # Change of Name
    if name_changed:
        certified_name_change_pdf_type = 'certificateOfNameChange'
        certified_name_change_encoded = get_filing_document(business['identifier'], filing.id,
                                                            certified_name_change_pdf_type, token)

        if certified_name_change_encoded:
            pdfs.append(
                {
                    'fileName': 'Certificate of Name Change.pdf',
                    'fileBytes': certified_name_change_encoded.decode('utf-8'),
                    'fileUrl': '',
                    'attachOrder': str(attach_order)
                }
            )
            attach_order += 1

    # Certified Rules
    if rules_changed:
        rules_pdf_type = 'certifiedRules'
        certified_rules_encoded = get_filing_document(business['identifier'], filing.id, rules_pdf_type, token)
        if certified_rules_encoded:
            pdfs.append(
                {
                    'fileName': 'Certified Rules.pdf',
                    'fileBytes': certified_rules_encoded.decode('utf-8'),
                    'fileUrl': '',
                    'attachOrder': str(attach_order)
                }
            )
            attach_order += 1

    # Certified Memorandum
    if memorandum_changed:
        certified_memorandum_pdf_type = 'certifiedMemorandum'
        certified_memorandum_encoded = get_filing_document(business['identifier'], filing.id,
                                                           certified_memorandum_pdf_type, token)
        if certified_memorandum_encoded:
            pdfs.append(
                {
                    'fileName': 'Certified Memorandum.pdf',
                    'fileBytes': certified_memorandum_encoded.decode('utf-8'),
                    'fileUrl': '',
                    'attachOrder': str(attach_order)
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
    sr_filing_pdf_type = 'specialResolutionApplication'
    sr_filing_pdf_encoded = get_filing_document(business['identifier'], filing.id, sr_filing_pdf_type, token)
    if sr_filing_pdf_encoded:
        pdfs.append(
            {
                'fileName': 'Special Resolution Application.pdf',
                'fileBytes': sr_filing_pdf_encoded.decode('utf-8'),
                'fileUrl': '',
                'attachOrder': str(attach_order)
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
                'attachOrder': str(attach_order)
            }
        )
        attach_order += 1

    return pdfs
