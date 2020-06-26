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
"""Email processing rules and actions for completeing incorporation."""
from __future__ import annotations

import base64
from http import HTTPStatus
from pathlib import Path

import requests
from entity_queue_common.service_utils import logger
from flask import current_app
from jinja2 import Template
from legal_api.models import Filing
from sentry_sdk import capture_message

from entity_emailer.email_processors import get_filing_info, get_recipients, substitute_template_parts


def _get_pdfs(stage: str, token: str, business: dict, filing: Filing, filing_date_time: str) -> list:
    """Get the pdfs for the incorporation output."""
    pdfs = []
    headers = {
        'Accept': 'application/pdf',
        'Authorization': f'Bearer {token}'
    }
    if stage == 'filed':
        # IA pdf
        inc_app = requests.get(
            f'{current_app.config.get("LEGAL_API_URL")}/businesses/{business["identifier"]}/filings/{filing.id}',
            headers=headers
        )
        if inc_app.status_code != HTTPStatus.OK:
            logger.error('Failed to get IA pdf for filing: %s', filing.id)
            capture_message(f'Email Queue: filing id={filing.id}, error=pdf generation', level='error')
        else:
            inc_app_encoded = base64.b64encode(inc_app.content)
            pdfs.append(
                {
                    'fileName': 'Incorporation Application.pdf',
                    'fileBytes': inc_app_encoded.decode('utf-8'),
                    'fileUrl': '',
                    'attachOrder': '1'
                }
            )
        # receipt pdf
        receipt = requests.post(
            f'{current_app.config.get("PAY_API_URL")}/{filing.payment_token}/receipts',
            json={
                'corpName': filing.filing_json['filing']['incorporationApplication']['nameRequest'].get(
                    'legalName', 'Numbered Company'),
                'filingDateTime': filing_date_time
            },
            headers=headers
        )
        if receipt.status_code != HTTPStatus.CREATED:
            logger.error('Failed to get receipt pdf for filing: %s', filing.id)
            capture_message(f'Email Queue: filing id={filing.id}, error=receipt generation', level='error')
        else:
            receipt_encoded = base64.b64encode(receipt.content)
            pdfs.append(
                {
                    'fileName': 'Receipt.pdf',
                    'fileBytes': receipt_encoded.decode('utf-8'),
                    'fileUrl': '',
                    'attachOrder': '2'
                }
            )
    if stage == 'registered':
        noa = requests.get(
            f'{current_app.config.get("LEGAL_API_URL")}/businesses/{business["identifier"]}/filings/{filing.id}'
            '?type=noa',
            headers=headers
        )
        if noa.status_code != HTTPStatus.OK:
            logger.error('Failed to get noa pdf for filing: %s', filing.id)
            capture_message(f'Email Queue: filing id={filing.id}, error=noa generation', level='error')
        else:
            noa_encoded = base64.b64encode(noa.content)
            pdfs.append(
                {
                    'fileName': 'Notice of Articles.pdf',
                    'fileBytes': noa_encoded.decode('utf-8'),
                    'fileUrl': '',
                    'attachOrder': '1'
                }
            )
        certificate = requests.get(
            f'{current_app.config.get("LEGAL_API_URL")}/businesses/{business["identifier"]}/filings/{filing.id}'
            '?type=certificate',
            headers=headers
        )
        if certificate.status_code != HTTPStatus.OK:
            logger.error('Failed to get certificate pdf for filing: %s', filing.id)
            capture_message(f'Email Queue: filing id={filing.id}, error=certificate generation', level='error')
        else:
            certificate_encoded = base64.b64encode(certificate.content)
            pdfs.append(
                {
                    'fileName': 'Incorporation Certificate.pdf',
                    'fileBytes': certificate_encoded.decode('utf-8'),
                    'fileUrl': '',
                    'attachOrder': '2'
                }
            )

    return pdfs


def process(email_msg: dict, token: str) -> dict:  # pylint: disable=too-many-locals
    """Build the email for Business Number notification."""
    logger.debug('incorp_notification: %s', email_msg)
    # get template and fill in parts
    template = Path(f'{current_app.config.get("TEMPLATE_PATH")}/BC-{email_msg["option"]}-success.html').read_text()
    filled_template = substitute_template_parts(template)

    # get template vars from filing
    filing, business, leg_tmz_filing_date, leg_tmz_effective_date = get_filing_info(email_msg['filingId'])

    # render template with vars
    jnja_template = Template(filled_template, autoescape=True)
    html_out = jnja_template.render(
        business=business,
        incorporationApplication=(filing.json)['filing']['incorporationApplication'],
        header=(filing.json)['filing']['header'],
        filing_date_time=leg_tmz_filing_date,
        effective_date_time=leg_tmz_effective_date,
        entity_dashboard_url=current_app.config.get('DASHBOARD_URL') +
        (filing.json)['filing']['business'].get('identifier', '')
    )

    # get attachments
    pdfs = _get_pdfs(email_msg['option'], token, business, filing, leg_tmz_filing_date)

    # get recipients
    recipients = get_recipients(email_msg['option'], filing.filing_json)

    # assign subject
    if email_msg['option'] == 'filed':
        subject = 'Confirmation of Filing from the Business Registry'
    elif email_msg['option'] == 'registered':
        subject = 'Incorporation Documents from the Business Registry'
    else:  # fallback case - should never happen
        subject = 'Notification from the BC Business Registry'

    return {
        'recipients': recipients,
        'requestBy': 'BCRegistries@gov.bc.ca',
        'content': {
            'subject': subject,
            'body': f'{html_out}',
            'attachments': pdfs
        }
    }
