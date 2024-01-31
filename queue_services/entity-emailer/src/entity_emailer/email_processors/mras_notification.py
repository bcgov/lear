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
"""Email processing actions for mras notification."""
from __future__ import annotations

from pathlib import Path

from flask import current_app, request
from jinja2 import Template

from entity_emailer.email_processors import get_filing_info, get_recipients, substitute_template_parts
from entity_emailer.services.logging import structured_log


def process(email_msg: dict) -> dict:
    """Build the email for mras notification."""
    structured_log(request, "DEBUG", f"mras_notification: {email_msg}")
    filing_type = email_msg["type"]
    # get template and fill in parts
    template = Path(f'{current_app.config.get("TEMPLATE_PATH")}/BC-MRAS.html').read_text()
    filled_template = substitute_template_parts(template)
    # get template info from filing
    filing, business, leg_tmz_filing_date, leg_tmz_effective_date = get_filing_info(email_msg["filingId"])

    # render template with vars
    jnja_template = Template(filled_template, autoescape=True)
    html_out = jnja_template.render(
        business=business,
        filing=(filing.json)["filing"]["incorporationApplication"],
        header=(filing.json)["filing"]["header"],
        filing_date_time=leg_tmz_filing_date,
        effective_date_time=leg_tmz_effective_date,
        filing_type=filing_type,
    )

    # get recipients
    recipients = get_recipients(email_msg["option"], filing.filing_json)

    return {
        "recipients": recipients,
        "requestBy": "BCRegistries@gov.bc.ca",
        "content": {
            "subject": "BC Business Registry Partner Information",
            "body": f"{html_out}",
            "attachments": [],
        },
    }
