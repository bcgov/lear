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
import base64
from datetime import datetime
from http import HTTPStatus
from pathlib import Path

import requests
from entity_queue_common.service_utils import logger
from flask import current_app
from jinja2 import Environment, FileSystemLoader, Template
from legal_api.models import Filing
from legal_api.utils.legislation_datetime import LegislationDatetime
from sentry_sdk import capture_message

from entity_emailer.email_processors import substitute_template_parts


ENV = Environment(loader=FileSystemLoader('email-templates'), autoescape=True)


def _get_pdfs(stage: str, token: str, business: dict, filing: Filing, filing_date_time: str):
    """Get the pdfs for the incorporation output."""
    pdfs = []
    if stage == 'filed':
        # IA pdf
        inc_app = requests.get(
            f'{current_app.config.get("LEGAL_API_URL")}/businesses/{business["identifier"]}/filings/{filing.id}',
            headers={
                'Accept': 'application/pdf',
                'Authorization': f'Bearer {token}'
            }
        )
        if inc_app.status_code != HTTPStatus.CREATED:
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
                'corpName': filing.filing_json['filing']['incorporationApplication']['nameRequest'].get('legalName'),
                'filingDateTime': filing_date_time
            },
            headers={
                'Accept': 'application/pdf',
                'Authorization': f'Bearer {token}'
            }
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
            f'{current_app.config.get("LEGAL_API_URL")}/businesses/{business["identifier"]}/filings/{filing.id}\
            ?type=noa',
            headers={
                'Accept': 'application/pdf',
                'Authorization': f'Bearer {token}'
            }
        )
        if noa.status_code != HTTPStatus.CREATED:
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
            f'{current_app.config.get("LEGAL_API_URL")}/businesses/{business["identifier"]}/filings/{filing.id}\
            ?type=certificate',
            headers={
                'Accept': 'application/pdf',
                'Authorization': f'Bearer {token}'
            }
        )
        if certificate.status_code != HTTPStatus.CREATED:
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


def _get_recipients(stage: str, filing_json: dict):
    """Get the recipients for the incorporation output."""
    recipients = filing_json['filing']['incorporationApplication']['contactPoint']['email']
    if stage == 'filed':
        parties = filing_json['filing']['incorporationApplication'].get('parties')
        comp_party_email = None
        for party in parties:
            for role in party['roles']:
                if role['roleType'] == 'Completing Party':
                    comp_party_email = party['officer']['email']
                    break
        recipients = f'{recipients}, {comp_party_email}'
    return recipients


def process(email_msg: dict, token: str):
    """Build the email for Business Number notification."""
    logger.debug('incorp_notification: %s', email_msg)
    # get template and fill in parts
    template = Path(f'email_templates/BC-{email_msg["option"]}-success.html').read_text()
    filled_template = substitute_template_parts(template)

    # get template vars from filing
    filing = Filing.find_by_id(email_msg['filingId'])
    filing_json = filing.json
    business = filing_json['filing']['business']
    filing_date = datetime.fromisoformat(filing.filing_date.isoformat())
    leg_tmz_filing_date = LegislationDatetime.as_legislation_timezone(filing_date).strftime('%Y-%m-%d %I:%M %p')
    effective_date = datetime.fromisoformat(filing.effective_date.isoformat())
    leg_tmz_effective_date = LegislationDatetime.as_legislation_timezone(effective_date).strftime('%Y-%m-%d %I:%M %p')

    # render template with vars
    jnja_template = Template(filled_template, autoescape=True)
    html_out = jnja_template.render(
        business=business,
        incorporationApplication=filing_json['filing']['incorporationApplication'],
        header=filing_json['filing']['header'],
        filing_date_time=leg_tmz_filing_date,
        effective_date_time=leg_tmz_effective_date,
        entity_dashboard_url=current_app.config.get('DASHBOARD_URL') +
        filing_json['filing']['business'].get('identifier', '')
    )

    # get attachments
    pdfs = _get_pdfs(email_msg['option'], token, business, filing, leg_tmz_filing_date)
    recipients = _get_recipients(email_msg['option'], filing.filing_json)
    return {
        'recipients': recipients,
        'requestBy': '',
        'content': {
            'subject': 'Incorporation Documents from the Business Registry',
            'body': f'{html_out}',
            'attachments': pdfs
        }
    }
