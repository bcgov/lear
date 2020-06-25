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
"""This module contains all of the Entity Email specific processors.

Processors hold the business logic for how an email is interpreted and sent.
"""
from __future__ import annotations

from datetime import datetime
from pathlib import Path

from flask import current_app
from legal_api.models import Filing
from legal_api.utils.legislation_datetime import LegislationDatetime


def get_filing_info(filing_id: str) -> (Filing, dict, dict, str, str):
    """Get filing info for the email."""
    filing = Filing.find_by_id(filing_id)
    business = (filing.json)['filing']['business']

    filing_date = datetime.fromisoformat(filing.filing_date.isoformat())
    leg_tmz_filing_date = LegislationDatetime.as_legislation_timezone(filing_date)
    hour = leg_tmz_filing_date.strftime('%I').lstrip('0')
    leg_tmz_filing_date = leg_tmz_filing_date.strftime(f'%B %d, %Y {hour}:%M %p Pacific Time')

    effective_date = datetime.fromisoformat(filing.effective_date.isoformat())
    leg_tmz_effective_date = LegislationDatetime.as_legislation_timezone(effective_date)
    hour = leg_tmz_effective_date.strftime('%I').lstrip('0')
    leg_tmz_effective_date = leg_tmz_effective_date.strftime(f'%B %d, %Y {hour}:%M %p Pacific Time')

    return filing, business, leg_tmz_filing_date, leg_tmz_effective_date

<<<<<<< Updated upstream

=======
>>>>>>> Stashed changes
def get_recipients(option: str, filing_json: dict) -> str:
    """Get the recipients for the email output."""
    recipients = ''
    if filing_json['filing'].get('incorporationApplication'):
        recipients = filing_json['filing']['incorporationApplication']['contactPoint']['email']
<<<<<<< Updated upstream
        if option in ['filed']:
=======
        if option in ['filed', 'bn']:
>>>>>>> Stashed changes
            parties = filing_json['filing']['incorporationApplication'].get('parties')
            comp_party_email = None
            for party in parties:
                for role in party['roles']:
                    if role['roleType'] == 'Completing Party':
                        comp_party_email = party['officer']['email']
                        break
            recipients = f'{recipients}, {comp_party_email}'
    return recipients


def substitute_template_parts(template_code: str) -> str:
    """Substitute template parts in main template.

    Template parts are marked by [[partname.html]] in templates.

    This functionality is restricted by:
    - markup must be exactly [[partname.html]] and have no extra spaces around file name
    - template parts can only be one level deep, ie: this rudimentary framework does not handle nested template
    parts. There is no recursive search and replace.
    """
    template_parts = [
        'business-dashboard-link',
        'business-info',
        'cra-notice',
        'footer',
        'header',
        'initiative-notice',
        'logo',
        'pdf-notice',
        'style',
        'whitespace-16px',
        'whitespace-24px'
    ]

    # substitute template parts - marked up by [[filename]]
    for template_part in template_parts:
        template_part_code = Path(f'{current_app.config.get("TEMPLATE_PATH")}/common/{template_part}.html').read_text()
        template_code = template_code.replace('[[{}.html]]'.format(template_part), template_part_code)

    return template_code
