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
"""Email processing rules and actions for Name Request before expiry, expiry, renewal, upgrade."""
from __future__ import annotations

from datetime import datetime
from enum import Enum
from http import HTTPStatus
from pathlib import Path

from entity_queue_common.service_utils import logger
from flask import current_app
from jinja2 import Template
from legal_api.services import NameXService
from legal_api.utils.legislation_datetime import LegislationDatetime

from entity_emailer.email_processors import substitute_template_parts


class Option(Enum):
    """NR notification option."""

    BEFORE_EXPIRY = 'before-expiry'
    EXPIRED = 'expired'
    RENEWAL = 'renewal'
    UPGRADE = 'upgrade'
    REFUND = 'refund'


def process(email_info: dict, option) -> dict:  # pylint: disable-msg=too-many-locals
    """
    Build the email for Name Request notification.

    valid values of option: Option
    """
    logger.debug('NR %s notification: %s', option, email_info)
    nr_number = email_info['identifier']
    template = Path(f'{current_app.config.get("TEMPLATE_PATH")}/NR-{option.upper()}.html').read_text()
    filled_template = substitute_template_parts(template)

    nr_response = NameXService.query_nr_number(nr_number)
    if nr_response.status_code != HTTPStatus.OK:
        logger.error('Failed to get nr info for name request: %s', nr_number)
        return {}

    nr_data = nr_response.json()

    expiration_date = ''
    if nr_data['expirationDate']:
        exp_date = datetime.fromisoformat(nr_data['expirationDate'])
        exp_date_tz = LegislationDatetime.as_legislation_timezone(exp_date)
        expiration_date = LegislationDatetime.format_as_report_string(exp_date_tz)

    refund_value = ''
    if option == Option.REFUND.value:
        refund_value = email_info.get('data', {}).get('request', {}).get('refundValue', None)

    legal_name = ''
    for n_item in nr_data['names']:
        if n_item['state'] in ('APPROVED', 'CONDITION'):
            legal_name = n_item['name']
            break

    # render template with vars
    mail_template = Template(filled_template, autoescape=True)
    html_out = mail_template.render(
        nr_number=nr_number,
        expiration_date=expiration_date,
        legal_name=legal_name,
        refund_value=refund_value
    )

    # get recipients
    recipients = nr_data['applicants']['emailAddress']
    if not recipients:
        return {}

    subjects = {
        Option.BEFORE_EXPIRY.value: 'Expiring Soon',
        Option.EXPIRED.value: 'Expired',
        Option.RENEWAL.value: 'Confirmation of Renewal',
        Option.UPGRADE.value: 'Confirmation of Upgrade',
        Option.REFUND.value: 'Refund request confirmation'
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
