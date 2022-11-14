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
"""Email processing rules and actions for Incorporation Application notifications."""
from __future__ import annotations

import base64
import re
from http import HTTPStatus
from pathlib import Path

import requests
from entity_queue_common.service_utils import logger
from flask import current_app
from jinja2 import Template
from legal_api.models import Business, Filing
from legal_api.services import NameXService
from sentry_sdk import capture_message

from entity_emailer.email_processors import get_filing_info, get_recipients, substitute_template_parts
from entity_emailer.email_processors.correction_notification import process as process_correction


FILING_TYPE_CONVERTER = {
    'incorporationApplication': 'IA',
    'annualReport': 'AR',
    'changeOfDirectors': 'COD',
    'changeOfAddress': 'COA',
    'alteration': 'ALT',
    'correction': 'CRCTN'
}


def _get_pdfs(
        status: str,
        token: str,
        business: dict,
        filing: Filing,
        filing_date_time: str,
        effective_date: str) -> list:
    # pylint: disable=too-many-locals, too-many-branches, too-many-statements, too-many-arguments
    """Get the pdfs for the incorporation output."""
    pdfs = []
    attach_order = 1
    headers = {
        'Accept': 'application/pdf',
        'Authorization': f'Bearer {token}'
    }
    legal_type = business.get('legalType', None)

    if filing.filing_type == 'correction':
        original_filing_type = filing.filing_json['filing']['correction']['correctedFilingType']
    if status == Filing.Status.PAID.value:
        # add filing pdf
        filing_pdf = requests.get(
            f'{current_app.config.get("LEGAL_API_URL")}/businesses/{business["identifier"]}/filings/{filing.id}',
            headers=headers
        )
        if filing_pdf.status_code != HTTPStatus.OK:
            logger.error('Failed to get pdf for filing: %s', filing.id)
            capture_message(f'Email Queue: filing id={filing.id}, error=pdf generation', level='error')
        else:
            filing_pdf_encoded = base64.b64encode(filing_pdf.content)
            if filing.filing_type == 'correction':
                file_name = original_filing_type[0].upper() + \
                    ' '.join(re.findall('[a-zA-Z][^A-Z]*', original_filing_type[1:]))
                file_name = f'{file_name} (Corrected)'
            else:
                file_name = filing.filing_type[0].upper() + \
                    ' '.join(re.findall('[a-zA-Z][^A-Z]*', filing.filing_type[1:]))
                if ar_date := filing.filing_json['filing'].get('annualReport', {}).get('annualReportDate'):
                    file_name = f'{ar_date[:4]} {file_name}'

            pdfs.append(
                {
                    'fileName': f'{file_name}.pdf',
                    'fileBytes': filing_pdf_encoded.decode('utf-8'),
                    'fileUrl': '',
                    'attachOrder': attach_order
                }
            )
            attach_order += 1
        # add receipt pdf
        if filing.filing_type == 'incorporationApplication' or (filing.filing_type == 'correction' and
                                                                original_filing_type == 'incorporationApplication'):
            corp_name = filing.filing_json['filing']['incorporationApplication']['nameRequest'].get(
                'legalName', 'Numbered Company')
        else:
            corp_name = business.get('legalName')

        # business_data won't be available for incorporationApplication
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
            capture_message(f'Email Queue: filing id={filing.id}, error=receipt generation', level='error')
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
    if status == Filing.Status.COMPLETED.value:
        if legal_type != Business.LegalTypes.COOP.value:
            # add notice of articles
            noa = requests.get(
                f'{current_app.config.get("LEGAL_API_URL")}/businesses/{business["identifier"]}/filings/{filing.id}'
                '?type=noticeOfArticles',
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
                        'attachOrder': attach_order
                    }
                )
                attach_order += 1

        if filing.filing_type == 'incorporationApplication' or (filing.filing_type == 'correction' and
                                                                original_filing_type == 'incorporationApplication' and
                                                                get_additional_info(filing).get('nameChange', False)):
            # add certificate
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
                file_name = 'Incorporation Certificate (Corrected).pdf' if filing.filing_type == 'correction' \
                    else 'Incorporation Certificate.pdf'
                pdfs.append(
                    {
                        'fileName': file_name,
                        'fileBytes': certificate_encoded.decode('utf-8'),
                        'fileUrl': '',
                        'attachOrder': attach_order
                    }
                )
                attach_order += 1

            if legal_type == Business.LegalTypes.COOP.value:
                # Add rules
                rules = requests.get(
                    f'{current_app.config.get("LEGAL_API_URL")}/businesses/{business["identifier"]}/filings/{filing.id}'
                    '?type=certifiedRules',
                    headers=headers
                )
                if rules.status_code != HTTPStatus.OK:
                    logger.error('Failed to get certifiedRules pdf for filing: %s', filing.id)
                    capture_message(f'Email Queue: filing id={filing.id}, error=certifiedRules generation',
                                    level='error')
                else:
                    certified_rules_encoded = base64.b64encode(rules.content)
                    pdfs.append(
                        {
                            'fileName': 'Certified Rules.pdf',
                            'fileBytes': certified_rules_encoded.decode('utf-8'),
                            'fileUrl': '',
                            'attachOrder': attach_order
                        }
                    )
                    attach_order += 1

                # Add memorandum
                memorandum = requests.get(
                    f'{current_app.config.get("LEGAL_API_URL")}/businesses/{business["identifier"]}/filings/{filing.id}'
                    '?type=certifiedMemorandum',
                    headers=headers
                )
                if memorandum.status_code != HTTPStatus.OK:
                    logger.error('Failed to get certifiedMemorandum pdf for filing: %s', filing.id)
                    capture_message(f'Email Queue: filing id={filing.id}, error=certifiedMemorandum generation',
                                    level='error')
                else:
                    certified_memorandum_encoded = base64.b64encode(memorandum.content)
                    pdfs.append(
                        {
                            'fileName': 'Certified Memorandum.pdf',
                            'fileBytes': certified_memorandum_encoded.decode('utf-8'),
                            'fileUrl': '',
                            'attachOrder': attach_order
                        }
                    )
                    attach_order += 1

        if filing.filing_type == 'alteration' and get_additional_info(filing).get('nameChange', False):
            # add certificate of name change
            certificate = requests.get(
                f'{current_app.config.get("LEGAL_API_URL")}/businesses/{business["identifier"]}/filings/{filing.id}'
                '?type=certificateOfNameChange',
                headers=headers
            )
            if certificate.status_code != HTTPStatus.OK:
                logger.error('Failed to get certificateOfNameChange pdf for filing: %s', filing.id)
                capture_message(f'Email Queue: filing id={filing.id}, error=certificateOfNameChange generation',
                                level='error')
            else:
                certificate_encoded = base64.b64encode(certificate.content)
                file_name = 'Certificate of Name Change.pdf'
                pdfs.append(
                    {
                        'fileName': file_name,
                        'fileBytes': certificate_encoded.decode('utf-8'),
                        'fileUrl': '',
                        'attachOrder': attach_order
                    }
                )
                attach_order += 1

    return pdfs


def process(email_info: dict, token: str) -> dict:  # pylint: disable=too-many-locals, , too-many-branches
    """Build the email for Business Number notification."""
    logger.debug('filing_notification: %s', email_info)
    # get template and fill in parts
    filing_type, status = email_info['type'], email_info['option']
    # get template vars from filing
    filing, business, leg_tmz_filing_date, leg_tmz_effective_date = get_filing_info(email_info['filingId'])
    legal_type = business.get('legalType')
    if filing_type == 'correction':
        if legal_type in ['SP', 'GP']:
            return process_correction(email_info, token)
        original_filing_type = filing.filing_json['filing']['correction']['correctedFilingType']
        if original_filing_type != 'incorporationApplication':
            return None
        original_filing_name = original_filing_type[0].upper() + ' '.join(re.findall('[a-zA-Z][^A-Z]*',
                                                                                     original_filing_type[1:]))
        filing_name = f'Correction of {original_filing_name}'
    else:
        filing_name = filing.filing_type[0].upper() + ' '.join(re.findall('[a-zA-Z][^A-Z]*', filing.filing_type[1:]))

    if filing_type == 'correction':
        template = Path(
            f'{current_app.config.get("TEMPLATE_PATH")}/BC-{FILING_TYPE_CONVERTER[filing_type]}-'
            f'{FILING_TYPE_CONVERTER[original_filing_type]}-{status}.html'
        ).read_text()
    else:
        template = Path(
            f'{current_app.config.get("TEMPLATE_PATH")}/BC-{FILING_TYPE_CONVERTER[filing_type]}-{status}.html'
        ).read_text()
    filled_template = substitute_template_parts(template)
    # render template with vars
    numbered_description = Business.BUSINESSES.get(legal_type, {}).get('numberedDescription')
    jnja_template = Template(filled_template, autoescape=True)
    filing_data = (filing.json)['filing'][f'{original_filing_type}'] if filing_type == 'correction' \
        else (filing.json)['filing'][f'{filing_type}']
    html_out = jnja_template.render(
        business=business,
        filing=filing_data,
        header=(filing.json)['filing']['header'],
        filing_date_time=leg_tmz_filing_date,
        effective_date_time=leg_tmz_effective_date,
        entity_dashboard_url=current_app.config.get('DASHBOARD_URL') +
        (filing.json)['filing']['business'].get('identifier', ''),
        email_header=filing_name.upper(),
        filing_type=filing_type,
        numbered_description=numbered_description,
        additional_info=get_additional_info(filing)
    )

    # get attachments
    pdfs = _get_pdfs(status, token, business, filing, leg_tmz_filing_date, leg_tmz_effective_date)

    # get recipients
    recipients = get_recipients(status, filing.filing_json, token)
    if not recipients:
        return {}

    # assign subject
    if status == Filing.Status.PAID.value:
        if filing_type == 'incorporationApplication':
            subject = 'Confirmation of Filing from the Business Registry'
        elif filing_type == 'correction':
            subject = f'Confirmation of Correction of {original_filing_name}'
        elif filing_type in ['changeOfAddress', 'changeOfDirectors']:
            address_director = [x for x in ['Address', 'Director'] if x in filing_type][0]
            subject = f'Confirmation of {address_director} Change'
        elif filing_type == 'annualReport':
            subject = 'Confirmation of Annual Report'
        elif filing_type == 'alteration':
            subject = 'Confirmation of Alteration from the Business Registry'

    elif status == Filing.Status.COMPLETED.value:
        if filing_type == 'incorporationApplication':
            subject = 'Incorporation Documents from the Business Registry'
        if filing_type == 'correction':
            subject = f'{original_filing_name} Correction Documents from the Business Registry'
        elif filing_type in ['changeOfAddress', 'changeOfDirectors', 'alteration', 'correction']:
            subject = 'Notice of Articles'

    if not subject:  # fallback case - should never happen
        subject = 'Notification from the BC Business Registry'

    if filing.filing_type == 'incorporationApplication':
        legal_name = \
            filing.filing_json['filing']['incorporationApplication']['nameRequest'].get('legalName', None)
    else:
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


def get_additional_info(filing: Filing) -> dict:
    """Populate any additional info required for a filing type."""
    additional_info = {}
    if filing.filing_type == 'correction':
        original_filing_type = filing.filing_json['filing']['correction']['correctedFilingType']
        if original_filing_type == 'incorporationApplication':
            additional_info['nameChange'] = NameXService.has_correction_changed_name(filing.filing_json)
    elif filing.filing_type == 'alteration':
        meta_data_alteration = filing.meta_data.get('alteration', {}) if filing.meta_data else {}
        additional_info['nameChange'] = 'toLegalName' in meta_data_alteration

    return additional_info
