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
"""Email processing rules and actions for Continuation In notifications."""
from __future__ import annotations

import base64
import re
from http import HTTPStatus
from pathlib import Path

import pycountry
import requests
from entity_queue_common.service_utils import logger
from flask import current_app
from jinja2 import Template
from legal_api.models import Business, Filing, ReviewResult

from entity_emailer.email_processors import (
    get_entity_dashboard_url,
    get_filing_document,
    get_filing_info,
    get_recipients,
    substitute_template_parts,
)


def _get_pdfs(
        status: str,
        token: str,
        business: dict,
        filing: Filing,
        filing_date_time: str,
        effective_date: str) -> list:
    # pylint: disable=too-many-locals, too-many-branches, too-many-statements, too-many-arguments
    """Get the outputs for the Continuation In notification."""
    pdfs = []
    attach_order = 1
    headers = {
        'Accept': 'application/pdf',
        'Authorization': f'Bearer {token}'
    }

    if status == Filing.Status.PAID.value:
        # add filing pdf
        filing_pdf_type = 'continuationIn'
        filing_pdf_encoded = get_filing_document(business['identifier'], filing.id, filing_pdf_type, token)
        if filing_pdf_encoded:
            pdfs.append(
                {
                    'fileName': 'Continuation Application - Pending.pdf',
                    'fileBytes': filing_pdf_encoded.decode('utf-8'),
                    'fileUrl': '',
                    'attachOrder': str(attach_order)
                }
            )
            attach_order += 1

        # add receipt
        if not (corp_name := business.get('legalName')):  # pylint: disable=superfluous-parens
            legal_type = business.get('legalType')
            corp_name = Business.BUSINESSES.get(legal_type, {}).get('numberedDescription')

        receipt = requests.post(
            f'{current_app.config.get("PAY_API_URL")}/{filing.payment_token}/receipts',
            json={
                'corpName': corp_name,
                'filingDateTime': filing_date_time,
                'effectiveDateTime': effective_date if effective_date != filing_date_time else '',
                'filingIdentifier': str(filing.id),
                'businessNumber': business.get('taxId', '')
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

    elif status == 'RESUBMITTED':
        # add filing pdf
        filing_pdf_type = 'continuationIn'
        filing_pdf_encoded = get_filing_document(business['identifier'], filing.id, filing_pdf_type, token)
        if filing_pdf_encoded:
            pdfs.append(
                {
                    'fileName': 'Continuation Application - Resubmitted.pdf',
                    'fileBytes': filing_pdf_encoded.decode('utf-8'),
                    'fileUrl': '',
                    'attachOrder': str(attach_order)
                }
            )
            attach_order += 1

    elif status == Filing.Status.COMPLETED.value:
        # add certificate of continuation
        certificate_pdf_type = 'certificateOfContinuation'
        certificate_encoded = get_filing_document(business['identifier'], filing.id, certificate_pdf_type, token)
        if certificate_encoded:
            pdfs.append(
                {
                    'fileName': 'Certificate of Continuation.pdf',
                    'fileBytes': certificate_encoded.decode('utf-8'),
                    'fileUrl': '',
                    'attachOrder': str(attach_order)
                }
            )
            attach_order += 1

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

    return pdfs


def process(email_info: dict, token: str) -> dict:  # pylint: disable=too-many-locals, , too-many-branches
    """Build the email for Continuation notification."""
    logger.debug('filing_notification: %s', email_info)

    # get template vars from email info
    filing_type, status = email_info['type'], email_info['option']

    # get template vars from filing
    filing, business, leg_tmz_filing_date, leg_tmz_effective_date = get_filing_info(email_info['filingId'])
    filing_name = filing.filing_type[0].upper() + ' '.join(re.findall('[a-zA-Z][^A-Z]*', filing.filing_type[1:]))
    filing_data = (filing.json)['filing'][f'{filing_type}']
    if status == Filing.Status.PAID.value:
        business = filing_data['nameRequest']
        business['identifier'] = filing.temp_reg
    legal_type = business.get('legalType')
    numbered_description = Business.BUSINESSES.get(legal_type, {}).get('numberedDescription')
    review_result = ReviewResult.get_last_review_result(filing.id)
    # encode newlines in review comment only
    latest_review_comment = review_result.comments.replace('\n', '\\n') if review_result else None

    # compute Foreign Jurisdiction string as in report.py and business_document.py
    country_code = filing_data['foreignJurisdiction']['country']
    region_code = filing_data['foreignJurisdiction']['region']
    country = pycountry.countries.get(alpha_2=country_code)
    region = None
    if region_code and region_code.upper() != 'FEDERAL':
        region = pycountry.subdivisions.get(code=f'{country_code}-{region_code}')
    foreign_jurisdiction = f'{region.name}, {country.name}' if region else country.name

    # get template and fill in parts
    template = Path(f'{current_app.config.get("TEMPLATE_PATH")}/CONT-IN-{status}.html').read_text()
    filled_template = substitute_template_parts(template)
    jnja_template = Template(filled_template, autoescape=True)

    # render template with vars
    html_out = jnja_template.render(
        business=business,
        filing=filing_data,
        filing_status=status,
        header=(filing.json)['filing']['header'],
        filing_date_time=leg_tmz_filing_date,
        effective_date_time=leg_tmz_effective_date,
        entity_dashboard_url=get_entity_dashboard_url(business.get('identifier'), token),
        email_header=filing_name.upper(),
        filing_type=filing_type,
        numbered_description=numbered_description,
        foreign_jurisdiction=foreign_jurisdiction,
        latest_review_comment=latest_review_comment
    )

    # decode newlines to <br> for html output
    html_out = html_out.replace('\\n', '<br>')

    # get attachments
    pdfs = _get_pdfs(status,
                     token,
                     business,
                     filing,
                     leg_tmz_filing_date,
                     leg_tmz_effective_date)

    # get recipients
    recipients = get_recipients(status, filing.filing_json, token, filing_type)
    if not recipients:
        return {}

    # assign subject
    legal_name = business.get('legalName', None)
    if status == Filing.Status.APPROVED.value:
        subject = 'Authorization Approved'
    if status == Filing.Status.REJECTED.value:
        subject = 'Authorization Rejected'
    elif status == Filing.Status.AWAITING_REVIEW.value:
        subject = 'Authorization Documents Received'
    elif status == Filing.Status.CHANGE_REQUESTED.value:
        subject = 'Changes Needed to Authorization'
    elif status == 'RESUBMITTED':
        subject = 'Authorization Updates Received'
    elif status == Filing.Status.COMPLETED.value:
        subject = 'Successful Continuation into B.C.'
    elif status == Filing.Status.PAID.value:
        subject = 'Continuation Application Received'

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
