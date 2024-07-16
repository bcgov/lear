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
"""Email processing rules and actions for involuntary_dissolution stage 1 overdue ARs notifications."""
from __future__ import annotations

from pathlib import Path

from entity_queue_common.service_utils import logger
from flask import current_app
from jinja2 import Template
from legal_api.models import Business, Furnishing

from entity_emailer.email_processors import get_entity_dashboard_url, get_jurisdictions, substitute_template_parts


PROCESSABLE_FURNISHING_NAMES = [
    Furnishing.FurnishingName.DISSOLUTION_COMMENCEMENT_NO_AR.name,
    Furnishing.FurnishingName.DISSOLUTION_COMMENCEMENT_NO_TR.name,
    Furnishing.FurnishingName.DISSOLUTION_COMMENCEMENT_NO_AR_XPRO.name,
    Furnishing.FurnishingName.DISSOLUTION_COMMENCEMENT_NO_TR_XPRO.name
]

PROCESSABLE_LEGAL_TYPES = [
    Business.LegalTypes.COMP,
    Business.LegalTypes.BC_ULC_COMPANY,
    Business.LegalTypes.BC_CCC,
    Business.LegalTypes.BCOMP
]


def process(email_info: dict, token: str) -> dict:  # pylint: disable=too-many-locals, , too-many-branches
    """Build the email for Involuntary dissolution notification."""
    logger.debug('involuntary_dissolution_stage_1_notification: %s', email_info)
    # get business
    furnishing_id = email_info['data']['furnishing']['furnishingId']
    furnishing = Furnishing.find_by_id(furnishing_id)
    business = furnishing.business
    business_identifier = business.identifier
    template = Path(
        f'{current_app.config.get("TEMPLATE_PATH")}/INVOL-DIS-STAGE-1.html'
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
    recipients.append(furnishing.email)  # furnishing email

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


def post_process(email_msg: dict, status: str):
    """Update corresponding furnishings entry as PROCESSED or FAILED depending on notification status."""
    furnishing_id = email_msg['data']['furnishing']['furnishingId']
    furnishing = Furnishing.find_by_id(furnishing_id)
    furnishing.status = Furnishing.FurnishingStatus[status]
    furnishing.save()


def is_processable(email_msg):
    """Determine if furnishing needs to be processed."""
    furnishing_id = email_msg['data']['furnishing']['furnishingId']
    furnishing = Furnishing.find_by_id(furnishing_id)
    business = furnishing.business
    return business.legal_type in PROCESSABLE_LEGAL_TYPES
