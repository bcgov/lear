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

from http import HTTPStatus
from pathlib import Path
import requests
from entity_queue_common.service_utils import logger
from flask import current_app
from jinja2 import Template
from legal_api.models import Business

from entity_emailer.email_processors import (
    get_recipient_from_auth,
    substitute_template_parts,
    get_entity_dashboard_url,
    get_extra_provincials,
)


def process(email_info: dict, token: str) -> dict:  # pylint: disable=too-many-locals, , too-many-branches
    """Build the email for Involuntary dissolution notification."""
    logger.debug('involuntary_dissolution_notification: %s', email_info)
    # get business
    identifier = email_info['identifier']
    business = Business.find_by_identifier(identifier)
    
    template = Path(
        f'{current_app.config.get("TEMPLATE_PATH")}/INVOLUNTARY-DIS.html'
    ).read_text()
    filled_template = substitute_template_parts(template)
    # render template with vars
    jnja_template = Template(filled_template, autoescape=True)
    # get state_names from mras response
    extra_provincials = get_extra_provincials(identifier, token)
    html_out = jnja_template.render(
        business=business.json(),
        entity_dashboard_url=get_entity_dashboard_url(business.get('identifier'), token),
        extra_provincials = extra_provincials
    )

    # get recipients
    recipients = []
    recipients.append(get_recipient_from_auth(business.identifier, token))  # business email

    recipients = list(set(recipients))
    recipients = ', '.join(filter(None, recipients)).strip()

    # assign subject
    subject = 'Involuntary Dissolution Documents from the Business Registry'
        
    if not subject:  # fallback case - should never happen
        subject = 'Notification from the BC Business Registry'

    legal_name = business.get('legalName', None)
    subject = f'{legal_name} - {subject}' if legal_name else subject

    return {
        'recipients': recipients,
        'requestBy': 'BCRegistries@gov.bc.ca',
        'content': {
            'subject': subject,
            'body': f'{html_out}'
        }
    }