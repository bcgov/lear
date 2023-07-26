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
"""Email processing rules and actions for Alteration notifications."""
from __future__ import annotations

import base64
import re
from http import HTTPStatus
from pathlib import Path
from typing import Optional

import requests
from entity_queue_common.service_utils import logger
from flask import current_app
from jinja2 import Template
from legal_api.models import Filing

from entity_emailer.email_processors import get_filing_info, get_recipient_from_auth, substitute_template_parts


def _get_pdfs(
        status: str,
        token: str,
        business: dict,
        filing: Filing,
        filing_date_time: str,
        effective_date: str,
        name_changed: bool,
        is_future_effective: bool) -> list:
    # pylint: disable=too-many-locals, too-many-branches, too-many-statements, too-many-arguments
    """Get the outputs for the Alteration notification."""
    pdfs = []
    attach_order = 1
    headers = {
        'Accept': 'application/pdf',
        'Authorization': f'Bearer {token}'
    }

    if status == Filing.Status.PAID.value:
        # add filing pdf
        filing_pdf = requests.get(
            f'{current_app.config.get("LEGAL_API_URL")}/businesses/{business["identifier"]}/filings/{filing.id}'
            f'?type=Alteration',
            headers=headers
        )
        if filing_pdf.status_code != HTTPStatus.OK:
            logger.error('Failed to get pdf for filing: %s', filing.id)
        else:
            filing_pdf_encoded = base64.b64encode(filing_pdf.content)
            pdfs.append(
                {
                    'fileName': 'Alteration Noticen.pdf',
                    'fileBytes': filing_pdf_encoded.decode('utf-8'),
                    'fileUrl': '',
                    'attachOrder': attach_order
                }
            )
            attach_order += 1

        corp_name = business.get('legalName')
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
                    'attachOrder': attach_order
                }
            )
            attach_order += 1
    elif status == Filing.Status.COMPLETED.value:
        # add notice of articles
        noa = requests.get(
            f'{current_app.config.get("LEGAL_API_URL")}/businesses/{business["identifier"]}/filings/{filing.id}'
            '?type=noticeOfArticles',
            headers=headers
        )
        if noa.status_code != HTTPStatus.OK:
            logger.error('Failed to get noa pdf for filing: %s', filing.id)
        else:
            noa_encoded = base64.b64encode(noa.content)
            pdfs.append(
                {
                    'fileName': 'Notice of Articles.pdf',
                    'fileBytes': noa_encoded.decode('utf-8'),
                    'fileUrl': '',
                    'attachOrder': attach_order
                }
            )
            attach_order += 1

    # Change of Name
    if name_changed and is_future_effective:
        name_change = requests.get(
            f'{current_app.config.get("LEGAL_API_URL")}/businesses/{business["identifier"]}/filings/{filing.id}'
            '?type=certificateOfNameChange',
            headers=headers
            )

        if name_change.status_code == HTTPStatus.OK:
            certified_name_change_encoded = base64.b64encode(name_change.content)
            pdfs.append(
                {
                    'fileName': 'Change of Name Certificate.pdf',
                    'fileBytes': certified_name_change_encoded.decode('utf-8'),
                    'fileUrl': '',
                    'attachOrder': attach_order
                }
            )
            attach_order += 1
        else:
            logger.error('Failed to get ChangeofNameCertificate pdf for filing: %s, status code: %s',
                         filing.id, name_change.status_code)

    return pdfs


def _get_template(is_future_effective: bool, status: str,  # pylint: disable=too-many-arguments
                  filing_type: str, filing: Filing,
                  business: dict, leg_tmz_filing_date: str, leg_tmz_effective_date: str,
                  name_changed: bool) -> str:
    """Return rendered template."""
    filing_name = filing.filing_type[0].upper() + ' '.join(re.findall('[a-zA-Z][^A-Z]*', filing.filing_type[1:]))

    template = Path(
        f'{current_app.config.get("TEMPLATE_PATH")}/BC-ALT-{status}.html'
    ).read_text()
    filled_template = substitute_template_parts(template)
    # render template with vars
    jnja_template = Template(filled_template, autoescape=True)
    filing_data = (filing.json)['filing'][f'{filing_type}']
    html_out = jnja_template.render(
        business=business,
        filing=filing_data,
        header=(filing.json)['filing']['header'],
        filing_date_time=leg_tmz_filing_date,
        effective_date_time=leg_tmz_effective_date,
        entity_dashboard_url=current_app.config.get('DASHBOARD_URL') + business.get('identifier', ''),
        email_header=filing_name.upper(),
        filing_type=filing_type,
        name_changed=name_changed
    )

    return html_out


def _get_recipients(filing: Filing) -> list:
    """Return recipients list."""
    recipients = []
    for party in filing.filing_json['filing']['Alteration'].get('parties', []):
        for role in party['roles']:
            if role['roleType'] in ('Partner', 'Proprietor', 'Completing Party'):
                recipients.append(party['officer'].get('email'))
                break

    if filing.filing_json['filing']['Alteration'].get('contactPoint'):
        recipients.append(filing.filing_json['filing']['Alteration']['contactPoint']['email'])

    recipients = list(set(recipients))
    recipients = list(filter(None, recipients))
    return recipients


def get_subject(status: str, business: dict) -> str:
    """Return subject."""
    subjects = {
        Filing.Status.PAID.value: 'Confirmation of Alteration from the Business Registry',
        Filing.Status.COMPLETED.value: 'Notice of Articles'
    }

    subject = subjects[status]
    if not subject:  # fallback case - should never happen
        subject = 'Notification from the BC Business Registry'

    legal_name = business.get('legalName', None)
    subject = f'{legal_name} - {subject}' if legal_name else subject

    return subject


def process(email_info: dict, token: str) -> Optional[dict]:  # pylint: disable=too-many-locals, , too-many-branches
    """Build the email for Alteration notification."""
    logger.debug('alteration_notification: %s', email_info)
    # get template and fill in parts
    filing_type, status = email_info['type'], email_info['option']
    # get template vars from filing
    filing, business, leg_tmz_filing_date, leg_tmz_effective_date = get_filing_info(email_info['filingId'])

    is_future_effective = filing.filing_json['header'].get('isFutureEffective')
    is_name_changed = False

    html_out = _get_template(is_future_effective,  # pylint: disable=too-many-function-args
                             status,
                             filing_type,
                             filing,
                             business,
                             leg_tmz_filing_date,
                             leg_tmz_effective_date,
                             is_name_changed)
    # get attachments
    pdfs = _get_pdfs(status, token, business, filing, leg_tmz_filing_date,
                     leg_tmz_effective_date, is_name_changed, is_future_effective)
    # get recipients
    recipients = get_recipient_from_auth(business.identifier, token)
    # assign subject
    subject = get_subject(email_info['option'], business)

    return {
        'recipients': recipients,
        'requestBy': 'BCRegistries@gov.bc.ca',
        'content': {
            'subject': subject,
            'body': f'{html_out}',
            'attachments': pdfs
        }
    }
