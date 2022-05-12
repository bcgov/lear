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
"""Email processing rules and actions for business number notification."""
from __future__ import annotations

from pathlib import Path

from entity_queue_common.service_utils import logger
from flask import current_app
from jinja2 import Template
from legal_api.models import Business, CorpType, Filing

from entity_emailer.email_processors import get_recipients, substitute_template_parts


def process(email_msg: dict) -> dict:
    """Build the email for Business Number notification."""
    logger.debug('bn notification: %s', email_msg)

    # get template and fill in parts
    template = Path(f'{current_app.config.get("TEMPLATE_PATH")}/BC-BN.html').read_text()
    filled_template = substitute_template_parts(template)

    # get filing and business json
    business = Business.find_by_identifier(email_msg['identifier'])
    filing_type = 'incorporationApplication'
    if business.legal_type in [Business.LegalTypes.SOLE_PROP.value, Business.LegalTypes.PARTNERSHIP.value]:
        filing_type = 'registration'
    filing = (Filing.get_a_businesses_most_recent_filing_of_a_type(business.id, filing_type))
    corp_type = CorpType.find_by_id(business.legal_type)

    # render template with vars
    jnja_template = Template(filled_template, autoescape=True)
    html_out = jnja_template.render(
        business=business.json(),
        entityDescription=corp_type.full_desc if corp_type else ''
    )

    # get recipients
    recipients = get_recipients(email_msg['option'], filing.filing_json, filing_type=filing_type)
    return {
        'recipients': recipients,
        'requestBy': 'BCRegistries@gov.bc.ca',
        'content': {
            'subject': f'{business.legal_name} - Business Number Information',
            'body': html_out,
            'attachments': []
        }
    }
