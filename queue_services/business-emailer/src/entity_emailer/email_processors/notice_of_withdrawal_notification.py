# Copyright © 2025 Province of British Columbia
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
"""Email processing rules and actions for Notice of Withdrawal notifications."""
import base64
import re
from http import HTTPStatus
from pathlib import Path

import requests
from flask import current_app
from jinja2 import Template
from entity_emailer.meta.filing import FilingMeta
from business_model.models import Business, Filing

from entity_emailer.email_processors import (
    get_filing_document,
    get_filing_info,
    get_recipient_from_auth,
    substitute_template_parts,
)
from entity_emailer.services import logger


def process(email_info: dict, token: str) -> dict:  # pylint: disable=too-many-locals
    """Build the email for Notice of Withdrawal notification."""
    logger.debug('notice_of_withdrawal_notification: %s', email_info)
    # get template and fill in parts
    filing_type = email_info['type']

    # get template variables from filing
    filing, business, leg_tmz_filing_date, leg_tmz_effective_date = get_filing_info(email_info['filingId'])
    legal_type = business.get('legalType')

    # display company name for existing businesses and temp businesses
    company_name = (
        business.get('legalName')
        or Business.BUSINESSES.get(legal_type, {}).get('numberedDescription')
        # fall back default value
        or 'Unknown Company'
    )
    # record to be withdrawn --> withdrawn filing display name
    withdrawn_filing = Filing.find_by_id(filing.withdrawn_filing_id)
    withdrawn_filing_display_name = FilingMeta.get_display_name(
        business['legalType'],
        withdrawn_filing.filing_type,
        withdrawn_filing.filing_sub_type
    )
    template = Path(
        f'{current_app.config.get("TEMPLATE_PATH")}/NOW-COMPLETED.html'
    ).read_text()
    filled_template = substitute_template_parts(template)
    # render template with vars
    jnja_template = Template(filled_template, autoescape=True)
    filing_data = (filing.json)['filing'][f'{filing_type}']
    filing_name = filing.filing_type[0].upper() + ' '.join(re.findall('[a-zA-Z][^A-Z]*', filing.filing_type[1:]))

    # default to None
    filing_id = None
    # show filing ID in email template when the withdrawn record is an IA, Amalg. or a ContIn
    if business.get('identifier').startswith('T'):
        filing_id = filing_data['filingId']

    html_out = jnja_template.render(
        business=business,
        filing=filing_data,
        header=(filing.json)['filing']['header'],
        company_name=company_name,
        filing_date_time=leg_tmz_filing_date,
        filing_id=filing_id,
        effective_date_time=leg_tmz_effective_date,
        withdrawnFilingType=withdrawn_filing_display_name,
        entity_dashboard_url=current_app.config.get('DASHBOARD_URL') +
                             (filing.json)['filing']['business'].get('identifier', ''),
        email_header=filing_name.upper(),
        filing_type=filing_type
    )

    # get attachments
    pdfs = _get_pdfs(token, business, filing, leg_tmz_filing_date, leg_tmz_effective_date)

    # get recipients
    identifier = filing.filing_json['filing']['business']['identifier']
    recipients = _get_contacts(identifier, token, withdrawn_filing)
    recipients = list(set(recipients))
    recipients = ', '.join(filter(None, recipients)).strip()

    # assign subject
    subject = 'Notice of Withdrawal filed Successfully'
    legal_name = company_name
    legal_name = 'Numbered Company' if legal_name.startswith(identifier) else legal_name
    subject = f'{legal_name} - {subject}'

    return {
        'recipients': recipients,
        'requestBy': 'BCRegistries@gov.bc.ca',
        'content': {
            'subject': subject,
            'body': f'{html_out}',
            'attachments': pdfs
        }
    }


def _get_pdfs(
    token: str,
    business: dict,
    filing: Filing,
    filing_date_time: str,
    effective_date: str) -> list:
    """Get the PDFs for the Notice of Withdrawal output."""
    pdfs = []
    attach_order = 1
    headers = {
        'Accept': 'application/pdf',
        'Authorization': f'Bearer {token}'
    }

    # add filing PDF
    filing_pdf_type = 'noticeOfWithdrawal'
    filing_pdf_encoded = get_filing_document(business['identifier'], filing.id, filing_pdf_type, token)
    if filing_pdf_encoded:
        pdfs.append(
            {
                'fileName': 'Notice of Withdrawal.pdf',
                'fileBytes': filing_pdf_encoded.decode('utf-8'),
                'fileUrl': '',
                'attachOrder': str(attach_order)
            }
        )
        attach_order += 1

    # add receipt PDF
    corp_name = business.get('legalName')
    if business.get('identifier').startswith('T'):
        business_data = None
    else:
        business_data = Business.find_by_internal_id(filing.business_id)
    receipt = requests.post(
        f'{current_app.config.get("PAY_API_URL")}/{filing.payment_token}/receipts',
        json={
            'corpName': corp_name,
            'filingDateTime': filing_date_time,
            'effectiveDateTime': effective_date if effective_date else '',
            'filingIdentifier': str(filing.id),
            'businessNumber': business_data.tax_id if business_data and business_data.tax_id else ''
        }, headers=headers)

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
            })
        attach_order += 1
    return pdfs


def _get_contacts(identifier, token, withdrawn_filing):
    recipients = []
    if identifier.startswith('T'):
        # get from withdrawn filing (FE new business filing)
        filing_type = withdrawn_filing.filing_type
        recipients.append(withdrawn_filing.filing_json['filing'][filing_type]['contactPoint']['email'])

        for party in withdrawn_filing.filing_json['filing'][filing_type]['parties']:
            for role in party['roles']:
                if role['roleType'] == 'Completing Party':
                    recipients.append(party['officer'].get('email'))
                    break
    else:
        recipients.append(get_recipient_from_auth(identifier, token))

    return recipients
