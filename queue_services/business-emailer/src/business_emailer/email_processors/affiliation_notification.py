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
"""Email processing rules and actions for Affiliation notifications."""
from __future__ import annotations

import re
from pathlib import Path

from flask import current_app
from jinja2 import Template

from business_emailer.email_processors import get_filing_info, get_recipients, substitute_template_parts


def process(email_info: dict, token: str) -> dict:  # pylint: disable=too-many-locals, , too-many-branches
    """Build the email for Affiliation notification."""
    current_app.logger.debug("filing_notification: %s", email_info)

    # get template vars from filing
    filing, business, leg_tmz_filing_date, leg_tmz_effective_date = \
        get_filing_info(email_info["filing"]["header"]["filingId"])
    filing_type = filing.filing_type
    status = filing.status
    filing_name = filing.filing_type[0].upper() + " ".join(re.findall("[a-zA-Z][^A-Z]*", filing.filing_type[1:]))

    template = Path(f'{current_app.config.get("TEMPLATE_PATH")}/BC-ALT-DRAFT.html').read_text()
    filled_template = substitute_template_parts(template)
    # render template with vars
    jnja_template = Template(filled_template, autoescape=True)
    filing_data = (filing.json)["filing"][f"{filing_type}"]
    html_out = jnja_template.render(
        business=business,
        filing=filing_data,
        header=(filing.json)["filing"]["header"],
        filing_date_time=leg_tmz_filing_date,
        effective_date_time=leg_tmz_effective_date,
        entity_dashboard_url=current_app.config.get("DASHBOARD_URL") +
                             (filing.json)["filing"]["business"].get("identifier", ""),
        email_header=filing_name.upper(),
        filing_type=filing_type
    )

    # get recipients
    recipients = get_recipients(status, filing.filing_json, token)
    if not recipients:
        return {}

    # assign subject
    legal_name = business.get("legalName", None)
    subject = f"{legal_name} - How to use BCRegistry.ca"

    return {
        "recipients": recipients,
        "requestBy": "BCRegistries@gov.bc.ca",
        "content": {
            "subject": subject,
            "body": f"{html_out}"
        }
    }
