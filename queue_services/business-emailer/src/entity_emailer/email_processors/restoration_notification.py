# Copyright © 2022 Province of British Columbia
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
"""Email processing rules and actions for Restoration Application notifications."""
from __future__ import annotations

import base64
import re
from http import HTTPStatus

import requests
from entity_queue_common.service_utils import logger
from flask import current_app
from jinja2 import Environment, FileSystemLoader
from business_model.models import Business, CorpType, Filing

from entity_emailer.email_processors import get_filing_document, get_filing_info


def _get_completed_pdfs(
        token: str,
        business: dict,
        filing: Filing) -> list:
    # pylint: disable=too-many-locals, too-many-branches, too-many-statements, too-many-arguments
    """Get the pdfs for the restoration output."""
    pdfs = []
    attach_order = 1

    # add notice of articles
    noa_pdf_type = 'noticeOfArticles'
    noa_encoded = get_filing_document(business['identifier'], filing.id, noa_pdf_type, token)
    if noa_encoded:
        pdfs.append(
            {
                'fileName': 'Notice of Articles.pdf',
                'fileBytes': noa_encoded.decode('utf-8'),
                'fileUrl': '',
                'attachOrder': str(attach_order)
            }
        )
        attach_order += 1
    # add certificate of restoration
    certificate_pdf_type = 'certificateOfRestoration'
    certificate_encoded = get_filing_document(business['identifier'], filing.id, certificate_pdf_type, token)
    if certificate_encoded:
        pdfs.append(
            {
                'fileName': 'Certificate of Restoration.pdf',
                'fileBytes': certificate_encoded.decode('utf-8'),
                'fileUrl': '',
                'attachOrder': str(attach_order)
            }
        )
        attach_order += 1

    return pdfs


def _get_paid_pdfs(
        token: str,
        business: dict,
        filing: Filing,
        filing_date_time: str,
        effective_date: str) -> list:
    # pylint: disable=too-many-locals, too-many-branches, too-many-statements, too-many-arguments
    """Get the pdfs for the restoration output."""
    pdfs = []
    attach_order = 1
    headers = {
        'Accept': 'application/pdf',
        'Authorization': f'Bearer {token}'
    }

    filing_pdf_type = 'restoration'
    filing_pdf_encoded = get_filing_document(business['identifier'], filing.id, filing_pdf_type, token)
    if filing_pdf_encoded:
        pdfs.append(
            {
                'fileName': 'Restoration Application.pdf',
                'fileBytes': filing_pdf_encoded.decode('utf-8'),
                'fileUrl': '',
                'attachOrder': str(attach_order)
            }
        )
        attach_order += 1
    name_request = filing.json['filing']['restoration']['nameRequest']
    corp_name = name_request.get('legalName')
    business_data = Business.find_by_internal_id(filing.business_id)
    receipt = requests.post(
        f'{current_app.config.get("PAY_API_URL")}/{filing.payment_token}/receipts',
        json={
            'corpName': corp_name,
            'filingDateTime': filing_date_time,
            'effectiveDateTime': effective_date if effective_date != filing_date_time else '',
            'filingIdentifier': str(filing.id),
            'businessNumber': business_data.tax_id if business_data and business_data.tax_id else ''
        },
        headers=headers
    )
    if receipt.status_code != HTTPStatus.CREATED:
        logger.error('Failed to get receipt pdf for filing: %s', filing.id)
    else:
        receipt_encoded = base64.b64encode(receipt.content)
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


def process(email_info: dict, token: str) -> dict:  # pylint: disable=too-many-locals, , too-many-branches
    """Build the email for Restoration notification."""
    logger.debug('registration_notification: %s', email_info)
    # get template and fill in parts
    filing_type, status = email_info['type'], email_info['option']
    # get template vars from filing
    filing, business, leg_tmz_filing_date, leg_tmz_effective_date = get_filing_info(email_info['filingId'])
    filing_name = filing.filing_type[0].upper() + ' '.join(re.findall('[a-zA-Z][^A-Z]*', filing.filing_type[1:]))
    business = business if business else filing.json['filing']['business']
    identifier = business.get('identifier')
    filing_business = filing.json['filing']['business']
    corp_type = CorpType.find_by_id(filing_business.get('legalType'))
    restoration_type = filing.json['filing']['restoration']['type']

    # create the jinja environment
    jinja_env = Environment(
        loader=FileSystemLoader(current_app.config.get('TEMPLATE_PATH')),
        autoescape=True
    )
    # look for a template in this format RES-fullRestoration-PAID.html
    # if the template doesn't exists use RES-PAID.html
    template = jinja_env.select_template([
        f'RES-{restoration_type}-{status}.jinja2',
        f'RES-{status}.jinja2'
    ])

    filing_data = filing.json['filing'][f'{filing_type}']
    html_out = template.render(
        business=business,
        filing=filing_data,
        header=filing.json['filing']['header'],
        filing_date_time=leg_tmz_filing_date,
        effective_date_time=leg_tmz_effective_date,
        entity_dashboard_url=current_app.config.get('DASHBOARD_URL') + identifier,
        email_header=filing_name.upper(),
        filing_type=filing_type,
        status=status,
        entityDescription=corp_type.full_desc if corp_type else ''
    )

    # get attachments
    if status == Filing.Status.PAID.value:
        pdfs = _get_paid_pdfs(token, business, filing, leg_tmz_filing_date, leg_tmz_effective_date)
    if status == Filing.Status.COMPLETED.value:
        pdfs = _get_completed_pdfs(token, business, filing)

    # get recipients
    recipients = []

    recipients.append(filing_data['contactPoint']['email'])

    for party in filing_data['parties']:
        for role in party['roles']:
            if role['roleType'] == 'Applicant':
                recipients.append(party['officer'].get('email'))
                break

    recipients = list(set(recipients))
    recipients = ', '.join(filter(None, recipients)).strip()

    # assign subject
    if status == Filing.Status.PAID.value:
        subject = 'Confirmation of Filing from the Business Registry'

    elif status == Filing.Status.COMPLETED.value:
        subject = 'Restoration Documents from the Business Registry'

    if not subject:  # fallback case - should never happen
        subject = 'Notification from the BC Business Registry'

    legal_name = business.get('legalName', None)
    subject = f'{legal_name} - {subject}' if legal_name else subject

    return {
        'recipients': recipients,
        'requestBy': 'BCRegistries@gov.bc.ca',
        'content': {
            'subject': subject,
            'body': f'{html_out}',
            'attachments': pdfs
        }
    }
