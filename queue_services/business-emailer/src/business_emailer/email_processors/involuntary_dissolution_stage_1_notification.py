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

import base64
from datetime import UTC, datetime
from http import HTTPStatus
from pathlib import Path

import requests
from flask import current_app
from jinja2 import Template

from business_emailer.email_processors import get_entity_dashboard_url, get_jurisdictions, substitute_template_parts
from business_model.models import Business, Furnishing

PROCESSABLE_FURNISHING_NAMES = [
    Furnishing.FurnishingName.DISSOLUTION_COMMENCEMENT_NO_AR.name,
    Furnishing.FurnishingName.DISSOLUTION_COMMENCEMENT_NO_TR.name,
    Furnishing.FurnishingName.DISSOLUTION_COMMENCEMENT_NO_AR_XPRO.name,
    Furnishing.FurnishingName.DISSOLUTION_COMMENCEMENT_NO_TR_XPRO.name
]


def process(email_info: dict, token: str) -> dict:  # pylint: disable=too-many-locals, , too-many-branches
    """Build the email for Involuntary dissolution notification."""
    current_app.logger.debug("involuntary_dissolution_stage_1_notification: %s", email_info)
    # get business
    furnishing_id = email_info["furnishing"]["furnishingId"]
    furnishing = Furnishing.find_by_id(furnishing_id)
    business = furnishing.business
    business_identifier = business.identifier
    # get template
    template = Path(
        f'{current_app.config.get("TEMPLATE_PATH")}/INVOL-DIS-STAGE-1.html'
    ).read_text(encoding="utf-8")
    filled_template = substitute_template_parts(template)
    # render template with vars
    jnja_template = Template(filled_template, autoescape=True)

    extra_provincials = []
    if furnishing.furnishing_name not in \
        [Furnishing.FurnishingName.DISSOLUTION_COMMENCEMENT_NO_AR_XPRO,
         Furnishing.FurnishingName.DISSOLUTION_COMMENCEMENT_NO_TR_XPRO]:
        # get response from get jurisdictions
        jurisdictions_response = get_jurisdictions(business_identifier, token)
        # get extra provincials array
        extra_provincials = get_extra_provincials(jurisdictions_response)

    html_out = jnja_template.render(
        business=business.json(),
        entity_dashboard_url=get_entity_dashboard_url(business_identifier, token),
        extra_provincials=extra_provincials,
        furnishing_name=furnishing.furnishing_name.name
    )
    # get recipients
    recipients = []
    recipients.append(furnishing.email)  # furnishing email

    recipients = list(set(recipients))
    recipients = ", ".join(filter(None, recipients)).strip()

    # get attachments
    pdfs = _get_pdfs(token, business, furnishing)

    legal_name = business.legal_name
    subject = f"Attention {business_identifier} - {legal_name}"

    return {
        "recipients": recipients,
        "requestBy": "BCRegistries@gov.bc.ca",
        "content": {
            "subject": subject,
            "body": f"{html_out}",
            "attachments": pdfs
        }
    }


def get_extra_provincials(response: dict):
    """Get extra provincials name."""
    extra_provincials = []
    if response:
        jurisdictions = response.get("jurisdictions", [])
        # List of NWPTA jurisdictions
        nwpta_jurisdictions = ["Alberta", "British Columbia", "Manitoba", "Saskatchewan"]
        for jurisdiction in jurisdictions:
            name = jurisdiction.get("name")
            if name and (name in nwpta_jurisdictions):
                extra_provincials.append(name)
        extra_provincials.sort()
    return extra_provincials


def post_process(email_msg: dict, status: str):
    """Update corresponding furnishings entry as PROCESSED or FAILED depending on notification status."""
    furnishing_id = email_msg["furnishing"]["furnishingId"]
    furnishing = Furnishing.find_by_id(furnishing_id)
    furnishing.status = status
    furnishing.processed_date = datetime.now(tz=UTC)
    furnishing.last_modified = datetime.now(tz=UTC)
    if status == Furnishing.FurnishingStatus.FAILED:
        furnishing.notes = "Failure to send email"
    furnishing.save()


def _get_pdfs(
        token: str,
        business: Business,
        furnishing: Furnishing
) -> list:
    """Get the pdf for the involuntary dissolution stage 1."""
    # get pdf for overdue ARs
    if furnishing.furnishing_name.name not in PROCESSABLE_FURNISHING_NAMES:
        return []
    headers = {
        "Accept": "application/pdf",
        "Authorization": f"Bearer {token}"
    }

    furnishing_pdf = requests.get(
        f'{current_app.config.get("LEGAL_API_URL")}/businesses/'
        f'{business.identifier}/furnishings/{furnishing.id}/document',
        headers=headers
    )

    if furnishing_pdf.status_code != HTTPStatus.OK:
        current_app.logger.error("Failed to get pdf for furnishing: %s", furnishing.id)
        return []

    if furnishing.furnishing_name in \
        [Furnishing.FurnishingName.DISSOLUTION_COMMENCEMENT_NO_AR_XPRO,
         Furnishing.FurnishingName.DISSOLUTION_COMMENCEMENT_NO_TR_XPRO]:
        filename = "Notice of Commencement of Cancellation.pdf"
    else:
        filename = "Notice of Commencement of Dissolution.pdf"

    furnishing_pdf_encoded = base64.b64encode(furnishing_pdf.content)

    return [{
        "fileName": filename,
        "fileBytes": furnishing_pdf_encoded.decode("utf-8"),
        "fileUrl": "",
        "attachOrder": "1"
    }]
