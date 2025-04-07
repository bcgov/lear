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
"""Email processing rules and actions for Correction notifications."""
from __future__ import annotations

import base64
import re
from http import HTTPStatus
from pathlib import Path
from typing import Optional

import requests
from flask import current_app
from jinja2 import Template
from business_model.models import Business, Filing

from entity_emailer.email_processors import get_filing_document, get_filing_info, substitute_template_parts
from entity_emailer.email_processors.special_resolution_helper import get_completed_pdfs
from entity_emailer.filing_helper import is_special_resolution_correction_by_filing_json
from entity_emailer.services import logger


# copied and pasted from legal_api.core.filing_helper
def _is_special_resolution_correction_by_meta_data(filing):
    """Check whether it is a special resolution correction."""
    # Check by using the meta_data, this is more permanent than the filing json.
    # This is used by reports (after the filer).
    if filing.meta_data and (correction_meta_data := filing.meta_data.get('correction')):
        # Note these come from the corrections filer.
        sr_correction_meta_data_keys = ['hasResolution', 'memorandumInResolution', 'rulesInResolution',
                                        'uploadNewRules', 'uploadNewMemorandum',
                                        'toCooperativeAssociationType', 'toLegalName']
        for key in sr_correction_meta_data_keys:
            if key in correction_meta_data:
                return True
    return False


def _get_pdfs(
    status: str,
    token: str,
    business: dict,
    filing: Filing,
    filing_date_time: str,
    effective_date: str,
    name_changed: bool) -> list:
    # pylint: disable=too-many-locals, too-many-branches, too-many-statements, too-many-arguments
    """Get the outputs for the correction notification."""
    pdfs = []
    attach_order = 1
    headers = {
        'Accept': 'application/pdf',
        'Authorization': f'Bearer {token}'
    }
    legal_type = business.get('legalType', None)
    is_cp_special_resolution = legal_type == 'CP' and is_special_resolution_correction_by_filing_json(
        filing.filing_json['filing']
    )

    if status == Filing.Status.PAID.value:
        # add filing pdf
        filing_pdf_type = 'correction'
        filing_pdf_encoded = get_filing_document(business['identifier'], filing.id, filing_pdf_type, token)
        if filing_pdf_encoded:
            pdfs.append(
                {
                    'fileName': 'Register Correction Application.pdf',
                    'fileBytes': filing_pdf_encoded.decode('utf-8'),
                    'fileUrl': '',
                    'attachOrder': str(attach_order)
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
                    'attachOrder': str(attach_order)
                }
            )
            attach_order += 1
    elif status == Filing.Status.COMPLETED.value:
        if legal_type in ('SP', 'GP'):
            # add corrected registration statement
            certificate_pdf_type = 'correctedRegistrationStatement'
            certificate_encoded = get_filing_document(business['identifier'], filing.id, certificate_pdf_type, token)
            if certificate_encoded:
                pdfs.append(
                    {
                        'fileName': 'Corrected - Registration Statement.pdf',
                        'fileBytes': certificate_encoded.decode('utf-8'),
                        'fileUrl': '',
                        'attachOrder': str(attach_order)
                    }
                )
                attach_order += 1
        elif legal_type in Business.CORPS:
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
        elif is_cp_special_resolution:
            rules_changed = bool(filing.filing_json['filing']['correction'].get('rulesFileKey'))
            memorandum_changed = bool(filing.filing_json['filing']['correction'].get('memorandumFileKey'))
            pdfs = get_completed_pdfs(token, business, filing, name_changed,
                                      rules_changed=rules_changed, memorandum_changed=memorandum_changed)
    return pdfs


def _get_template(prefix: str, status: str, filing_type: str, filing: Filing,  # pylint: disable=too-many-arguments
                  business: dict, leg_tmz_filing_date: str, leg_tmz_effective_date: str,
                  name_changed: bool) -> str:
    """Return rendered template."""
    filing_name = filing.filing_type[0].upper() + ' '.join(re.findall('[a-zA-Z][^A-Z]*', filing.filing_type[1:]))

    template = Path(
        f'{current_app.config.get("TEMPLATE_PATH")}/{prefix}-CRCTN-{status}.html'
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
    for party in filing.filing_json['filing']['correction'].get('parties', []):
        for role in party['roles']:
            if role['roleType'] in ('Partner', 'Proprietor', 'Completing Party'):
                recipients.append(party['officer'].get('email'))
                break

    if filing.filing_json['filing']['correction'].get('contactPoint'):
        recipients.append(filing.filing_json['filing']['correction']['contactPoint']['email'])

    recipients = list(set(recipients))
    recipients = list(filter(None, recipients))
    return recipients


def get_subject(status: str, prefix: str, business: dict) -> str:
    """Return subject."""
    subjects = {
        Filing.Status.PAID.value: 'Confirmation of correction' if prefix == 'CP-SR' else
        'Confirmation of Filing from the Business Registry',
        Filing.Status.COMPLETED.value: 'Correction Documents from the Business Registry'
    }

    subject = subjects[status]
    if not subject:  # fallback case - should never happen
        subject = 'Notification from the BC Business Registry'

    legal_name = business.get('legalName', None)
    subject = f'{legal_name} - {subject}' if legal_name else subject

    return subject


def process(email_info: dict, token: str) -> Optional[dict]:  # pylint: disable=too-many-locals, , too-many-branches
    """Build the email for Correction notification."""
    logger.debug('correction_notification: %s', email_info)
    # get template and fill in parts
    filing_type, status = email_info['type'], email_info['option']
    # get template vars from filing
    filing, business, leg_tmz_filing_date, leg_tmz_effective_date = get_filing_info(email_info['filingId'])

    prefix = 'BC'
    legal_type = business.get('legalType', None)
    name_changed = False

    if legal_type in ['SP', 'GP']:
        prefix = 'FIRM'
    elif legal_type in Business.CORPS:
        original_filing_type = filing.filing_json['filing']['correction']['correctedFilingType']
        if original_filing_type in ['annualReport', 'changeOfAddress', 'changeOfDirectors']:
            return None
    elif legal_type == 'CP' and is_special_resolution_correction_by_filing_json(
        filing.filing_json['filing']
    ):
        prefix = 'CP-SR'
        name_changed = 'requestType' in filing.filing_json['filing']['correction'].get('nameRequest', {})
    else:
        return None

    html_out = _get_template(prefix,  # pylint: disable=too-many-function-args
                             status,
                             filing_type,
                             filing,
                             business,
                             leg_tmz_filing_date,
                             leg_tmz_effective_date,
                             name_changed)
    # get attachments
    pdfs = _get_pdfs(status, token, business, filing, leg_tmz_filing_date, leg_tmz_effective_date, name_changed)
    # get recipients
    recipients = _get_recipients(filing)
    recipients = ', '.join(filter(None, recipients)).strip()
    # assign subject
    subject = get_subject(email_info['option'], prefix, business)

    return {
        'recipients': recipients,
        'requestBy': 'BCRegistries@gov.bc.ca',
        'content': {
            'subject': subject,
            'body': f'{html_out}',
            'attachments': pdfs
        }
    }
