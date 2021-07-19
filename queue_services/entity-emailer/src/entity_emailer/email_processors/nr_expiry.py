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
"""Email processing rules and actions for Name Request before expiry and expiry."""
from __future__ import annotations

from http import HTTPStatus
from pathlib import Path

from entity_queue_common.service_utils import logger
from flask import current_app
from jinja2 import Template
from legal_api.services import NameXService
from sentry_sdk import capture_message

from entity_emailer.email_processors import substitute_template_parts


def process(email_info: dict, option) -> dict:
    """
    Build the email for Name Request notification.

    valid values of option: 'before-expiry', 'expired'
    """
    logger.debug('NR_notification: %s', email_info)
    nr_number = email_info['nrNumber']
    template = Path(f'{current_app.config.get("TEMPLATE_PATH")}/NR-{option.upper()}.html').read_text()
    filled_template = substitute_template_parts(template)
    # render template with vars
    mail_template = Template(filled_template, autoescape=True)
    html_out = mail_template.render(
        nr_number=nr_number
    )

    nr_response = NameXService.query_nr_number(nr_number)
    if nr_response.status_code != HTTPStatus.OK:
        logger.error('Failed to get nr info for name request: %s', nr_number)
        capture_message(f'Email Queue: nr_id={nr_number}, error=receipt generation', level='error')
        return {}

    nr_data = nr_response.json()

    # get recipients
    recipients = nr_data['applicants']['emailAddress']
    if not recipients:
        return {}

    subjects = {
        'before-expiry': 'Expiring Soon',
        'expired': 'Expired'
    }

    return {
        'recipients': recipients,
        'requestBy': 'BCRegistries@gov.bc.ca',
        'content': {
            'subject': f'{nr_number} - {subjects[option]}',
            'body': f'{html_out}',
            'attachments': []
        }
    }
