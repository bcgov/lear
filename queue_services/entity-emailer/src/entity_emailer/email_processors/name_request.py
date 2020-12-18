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
"""Email processing rules and actions for Name Request Payment Completion."""
from __future__ import annotations

import base64
from http import HTTPStatus
from pathlib import Path

import requests
from entity_queue_common.service_utils import logger
from flask import current_app
from jinja2 import Template
from legal_api.services import NameXService
from sentry_sdk import capture_message

from entity_emailer.email_processors import substitute_template_parts


def process(email_info: dict) -> dict:
    """Build the email for Name Request notification."""
    logger.debug('NR_notification: %s', email_info)
    nr_number = email_info['identifier']
    template = Path(f'{current_app.config.get("TEMPLATE_PATH")}/NR-PAID.html').read_text()
    filled_template = substitute_template_parts(template)
    # render template with vars
    mail_template = Template(filled_template, autoescape=True)
    html_out = mail_template.render(
        identifier=nr_number
    )

    nr_response = NameXService.query_nr_number(nr_number)
    if nr_response.status_code != HTTPStatus.OK:
        logger.error('Failed to get nr info for name request: %s', nr_number)
        capture_message(f'Email Queue: nr_id={nr_number}, error=receipt generation', level='error')
        return {}

    nr_data = nr_response.json()
    # get attachments
    pdfs = _get_pdfs(nr_data)
    if not pdfs:
        return {}

    # get recipients
    recipients = nr_data['applicants']['emailAddress']
    if not recipients:
        return {}

    subject = f'{nr_number} - Receipt from Corporate Registry'

    return {
        'recipients': recipients,
        'requestBy': 'BCRegistries@gov.bc.ca',
        'content': {
            'subject': subject,
            'body': f'{html_out}',
            'attachments': pdfs
        }
    }


def _get_pdfs(nr_data: dict) -> list:
    """Get the receipt for the name request application."""
    pdfs = []
    token = get_nr_bearer_token()
    if token:
        nr_id = nr_data['id']
        payment_info = requests.get(
            f'{current_app.config.get("NAMEX_SVC_URL")}payments/{nr_id}',
            headers={
                'Content-Type': 'application/json',
                'Authorization': 'Bearer ' + token
            }
        )
        if payment_info.status_code != HTTPStatus.OK:
            logger.error('Failed to get payment info for name request: %s', nr_id)
            capture_message(f'Email Queue: nr_id={nr_id}, error=receipt generation', level='error')
        else:
            payment_info = payment_info.json()
            payment_id = payment_info[0]['payment']['id']
            receipt = requests.post(
                f'{current_app.config.get("NAMEX_SVC_URL")}payments/{payment_id}/receipt',
                json={},
                headers={
                    'Accept': 'application/pdf',
                    'Authorization': f'Bearer {token}'
                }
            )
            if receipt.status_code != HTTPStatus.OK:
                logger.error('Failed to get receipt pdf for name request: %s', nr_id)
                capture_message(f'Email Queue: nr_id={nr_id}, error=receipt generation', level='error')
            else:
                receipt_encoded = base64.b64encode(receipt.content)
                pdfs.append(
                    {
                        'fileName': 'Receipt.pdf',
                        'fileBytes': receipt_encoded.decode('utf-8'),
                        'fileUrl': '',
                        'attachOrder': '1'
                    }
                )
    return pdfs


def get_nr_bearer_token():
    """Get a valid Bearer token for the Name Request Service."""
    token_url = current_app.config.get('NAMEX_AUTH_SVC_URL')
    client_id = current_app.config.get('NAMEX_SERVICE_CLIENT_USERNAME')
    client_secret = current_app.config.get('NAMEX_SERVICE_CLIENT_SECRET')

    data = 'grant_type=client_credentials'
    # get service account token
    res = requests.post(url=token_url,
                        data=data,
                        headers={'content-type': 'application/x-www-form-urlencoded'},
                        auth=(client_id, client_secret))
    try:
        return res.json().get('access_token')
    except Exception:  # pylint: disable=broad-except
        logger.error('Failed to get nr token')
        capture_message('Failed to get nr token', level='error')
        return None
