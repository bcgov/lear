# Copyright © 2021 Province of British Columbia
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
"""Email processing rules and actions for Dissolution Application notifications."""
from __future__ import annotations

import base64
import re
from http import HTTPStatus
from pathlib import Path

import requests
from flask import current_app
from jinja2 import Template
from business_model.models import Business, Filing, UserRoles

from business_emailer.email_processors import (
    get_filing_document,
    get_filing_info,
    get_recipient_from_auth,
    get_user_email_from_auth,
    substitute_template_parts,
)
from business_emailer.services import logger


def _get_pdfs(
    status: str,
    token: str,
    business: dict,
    filing: Filing,
    filing_date_time: str,
    effective_date: str
) -> list:
    # pylint: disable=too-many-locals, too-many-branches, too-many-statements, too-many-arguments
    """Get the pdfs for the dissolution output."""
    pdfs = []
    attach_order = 1
    headers = {
        'Accept': 'application/pdf',
        'Authorization': f'Bearer {token}'
    }
    legal_type = business.get('legalType', None)

    if status == Filing.Status.PAID.value:
        # add filing pdf
        if legal_type not in ['SP', 'GP']:
            filing_pdf_type = 'dissolution'
            filing_pdf_encoded = get_filing_document(business['identifier'], filing.id, filing_pdf_type, token)
            if filing_pdf_encoded:
                pdfs.append(
                    {
                        'fileName': 'Voluntary Dissolution Application.pdf',
                        'fileBytes': filing_pdf_encoded.decode('utf-8'),
                        'fileUrl': '',
                        'attachOrder': str(attach_order)
                    }
                )
                attach_order += 1

        corp_name = business.get('legalName')
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
    elif status == Filing.Status.COMPLETED.value:
        if legal_type in ['SP', 'GP']:
            filing_pdf_type = 'dissolution'
            filing_pdf_encoded = get_filing_document(business['identifier'], filing.id, filing_pdf_type, token)
            if filing_pdf_encoded:
                pdfs.append(
                    {
                        'fileName': 'Statement of Dissolution.pdf',
                        'fileBytes': filing_pdf_encoded.decode('utf-8'),
                        'fileUrl': '',
                        'attachOrder': str(attach_order)
                    }
                )
                attach_order += 1
        else:
            if filing.filing_sub_type != 'administrative':
                # add certificateOfDissolution, suppress certificate of dissolution for admin dissolution
                certificate_pdf_type = 'certificateOfDissolution'
                certificate_encoded = get_filing_document(business['identifier'], filing.id,
                                                          certificate_pdf_type, token)
                if certificate_encoded:
                    pdfs.append(
                        {
                            'fileName': 'Certificate of Dissolution.pdf',
                            'fileBytes': certificate_encoded.decode('utf-8'),
                            'fileUrl': '',
                            'attachOrder': str(attach_order)
                        }
                    )
                    attach_order += 1

            if legal_type == Business.LegalTypes.COOP.value:
                # certifiedAffidavit
                certified_affidavit_pdf_type = 'affidavit'
                certified_affidavit_encoded = get_filing_document(business['identifier'], filing.id,
                                                                  certified_affidavit_pdf_type, token)
                if certified_affidavit_encoded:
                    pdfs.append(
                        {
                            'fileName': 'Certified Affidavit.pdf',
                            'fileBytes': certified_affidavit_encoded.decode('utf-8'),
                            'fileUrl': '',
                            'attachOrder': str(attach_order)
                        }
                    )
                    attach_order += 1

                # specialResolution
                special_resolution_pdf_type = 'specialResolution'
                special_resolution_encoded = get_filing_document(business['identifier'], filing.id,
                                                                 special_resolution_pdf_type, token)
                if special_resolution_encoded:
                    pdfs.append(
                        {
                            'fileName': 'Certified Special Resolution.pdf',
                            'fileBytes': special_resolution_encoded.decode('utf-8'),
                            'fileUrl': '',
                            'attachOrder': str(attach_order)
                        }
                    )
                    attach_order += 1

    return pdfs


def process(email_info: dict, token: str) -> dict:  # pylint: disable=too-many-locals, , too-many-branches
    """Build the email for Dissolution notification."""
    logger.debug('dissolution_notification: %s', email_info)
    # get template and fill in parts
    filing_type, status = email_info['type'], email_info['option']
    # get template vars from filing
    filing, business, leg_tmz_filing_date, leg_tmz_effective_date = get_filing_info(email_info['filingId'])
    filing_name = filing.filing_type[0].upper() + ' '.join(re.findall('[a-zA-Z][^A-Z]*', filing.filing_type[1:]))
    legal_type = business.get('legalType', None)

    template = Path(
        f'{current_app.config.get("TEMPLATE_PATH")}/DIS-{status}.html'
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
        entity_dashboard_url=current_app.config.get('DASHBOARD_URL') +
                             (filing.json)['filing']['business'].get('identifier', ''),
        email_header=filing_name.upper(),
        filing_type=filing_type
    )

    # get attachments
    pdfs = _get_pdfs(status, token, business, filing, leg_tmz_filing_date, leg_tmz_effective_date)

    # get recipients
    identifier = filing.filing_json['filing']['business']['identifier']
    recipients = []
    recipients.append(get_recipient_from_auth(identifier, token))

    if filing.submitter_roles and UserRoles.staff in filing.submitter_roles:
        # when staff file a dissolution documentOptionalEmail may contain completing party email
        recipients.append(filing.filing_json['filing']['header'].get('documentOptionalEmail'))
    else:
        recipients.append(get_user_email_from_auth(filing.filing_submitter.username, token))

    if legal_type in ['SP', 'GP']:  # Send email to all proprietor, partner, completing party
        business_data = Business.find_by_internal_id(filing.business_id)
        for party in filing.filing_json['filing']['dissolution']['parties']:
            if party['officer'].get('email'):
                recipients.append(party['officer']['email'])
        for party_role in business_data.party_roles.all():
            if party_role.party.email:
                recipients.append(party_role.party.email)
    else:
        for party in filing.filing_json['filing']['dissolution']['parties']:
            for role in party['roles']:
                if role['roleType'] == 'Custodian':
                    recipients.append(party['officer']['email'])
                    break

    recipients = list(set(recipients))
    recipients = ', '.join(filter(None, recipients)).strip()

    # assign subject
    if status == Filing.Status.PAID.value:
        if legal_type in ['SP', 'GP']:
            subject = 'Confirmation of Filing from the Business Registry'
        else:
            subject = 'Voluntary dissolution'

    elif status == Filing.Status.COMPLETED.value:
        if legal_type in ['SP', 'GP']:
            subject = 'Dissolution Documents from the Business Registry'
        else:
            subject = 'Confirmation of Dissolution from the Business Registry'

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
