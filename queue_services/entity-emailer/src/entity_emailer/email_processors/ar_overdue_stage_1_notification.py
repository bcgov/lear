# Copyright © 2024 Province of British Columbia
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
"""Email processing rules and actions for stage 1 overdue ARs notifications."""
from __future__ import annotations

from pathlib import Path

from entity_queue_common.service_utils import logger
from flask import current_app
from jinja2 import Template
from legal_api.models import Business, Furnishing

from entity_emailer.email_processors import (
    get_entity_dashboard_url,
    get_jurisdictions,
    get_recipient_from_auth,
    substitute_template_parts,
)


def process(email_info: dict, token: str) -> dict:  # pylint: disable=too-many-locals, , too-many-branches
    """Build the email for Involuntary dissolution notification."""
    logger.debug('ar_overdue_stage_1_notification: %s', email_info)
    # get business
    business_identifier = email_info['identifier']
    business = Business.find_by_identifier(business_identifier)
    template = Path(
        f'{current_app.config.get("TEMPLATE_PATH")}/AR_OVERDUE_STAGE_1.html'
    ).read_text()
    filled_template = substitute_template_parts(template)
    # render template with vars
    jnja_template = Template(filled_template, autoescape=True)
    # get response from get jurisdictions
    jurisdictions_response = get_jurisdictions(business_identifier, token)
    # get extra provincials array
    extra_provincials = get_extra_provincials(jurisdictions_response)
    html_out = jnja_template.render(
        business=business.json(),
        entity_dashboard_url=get_entity_dashboard_url(business_identifier, token),
        extra_provincials=extra_provincials
    )
    # get recipients
    recipients = []
    recipients.append(get_recipient_from_auth(business_identifier, token))  # business email

    recipients = list(set(recipients))
    recipients = ', '.join(filter(None, recipients)).strip()

    legal_name = business.legal_name
    subject = f'Attention {business_identifier} - {legal_name}'

    return {
        'recipients': recipients,
        'requestBy': 'BCRegistries@gov.bc.ca',
        'content': {
            'subject': subject,
            'body': f'{html_out}'
        }
    }


def get_extra_provincials(response: dict):
    """Get extra provincials name."""
    extra_provincials = []
    if response:
        jurisdictions = response.get('jurisdictions', [])
        for jurisdiction in jurisdictions:
            name = jurisdiction.get('name')
            if name:
                extra_provincials.append(name)

    return extra_provincials


def update_furnishing_status(furnishing_id: int, status: str):
    """Update corresponding furnishings entry as PROCESSED or FAILED depending on notification status."""
    furnishing = Furnishing.find_by_id(furnishing_id)
    furnishing.status = status
    furnishing.save()
