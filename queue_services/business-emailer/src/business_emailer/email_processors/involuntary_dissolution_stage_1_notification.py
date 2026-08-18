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

from business_emailer.email_processors import substitute_template_parts
from business_model.models import Business, Furnishing

PROCESSABLE_FURNISHING_NAMES = [
    Furnishing.FurnishingName.DISSOLUTION_COMMENCEMENT_NO_AR.name,
    Furnishing.FurnishingName.DISSOLUTION_COMMENCEMENT_NO_TR.name,
    Furnishing.FurnishingName.DISSOLUTION_COMMENCEMENT_NO_AR_XPRO.name,
    Furnishing.FurnishingName.DISSOLUTION_COMMENCEMENT_NO_TR_XPRO.name
]

XPRO_FURNISHING_NAMES = [
    Furnishing.FurnishingName.DISSOLUTION_COMMENCEMENT_NO_AR_XPRO,
    Furnishing.FurnishingName.DISSOLUTION_COMMENCEMENT_NO_TR_XPRO
]

# NWPTA partner jurisdictions a business can be extraprovincially registered in
NWPTA_JURISDICTION_IDS = ["AB", "MB", "SK"]

FURNISHING_CONTENT = {
    Furnishing.FurnishingName.DISSOLUTION_COMMENCEMENT_NO_AR.name: {
        "action": "dissolved",
        "delay_type": "dissolution",
        "reason_title": "overdue annual reports",
        "reason_description": "you haven't filed the required annual reports",
        "next_step_action": "file any outstanding annual reports",
        "attachment_name": "Notice of Commencement of Dissolution"
    },
    Furnishing.FurnishingName.DISSOLUTION_COMMENCEMENT_NO_TR.name: {
        "action": "dissolved",
        "delay_type": "dissolution",
        "reason_title": "failure to file a post restoration transition application",
        "reason_description": "you haven't filed the required post restoration transition application",
        "next_step_action": "file your post restoration transition application",
        "attachment_name": "Notice of Commencement of Dissolution"
    },
    Furnishing.FurnishingName.DISSOLUTION_COMMENCEMENT_NO_AR_XPRO.name: {
        "action": "cancelled",
        "delay_type": "cancellation",
        "reason_title": "overdue annual reports",
        "reason_description": "you haven't filed the required annual reports",
        "next_step_action": "file any outstanding annual reports",
        "attachment_name": "Notice of Commencement of Cancellation"
    },
    Furnishing.FurnishingName.DISSOLUTION_COMMENCEMENT_NO_TR_XPRO.name: {
        "action": "cancelled",
        "delay_type": "cancellation",
        "reason_title": "failure to file a post restoration transition application",
        "reason_description": "you haven't filed the required post restoration transition application",
        "next_step_action": "file your post restoration transition application",
        "attachment_name": "Notice of Commencement of Cancellation"
    }
}


def process(email_info: dict, token: str) -> dict:
    """Build the email for Involuntary dissolution notification."""
    current_app.logger.debug("involuntary_dissolution_stage_1_notification: %s", email_info)
    # get business
    furnishing_id = email_info["furnishing"]["furnishingId"]
    furnishing = Furnishing.find_by_id(furnishing_id)
    business = furnishing.business
    business_identifier = business.identifier
    business_name = business.legal_name
    content = FURNISHING_CONTENT[furnishing.furnishing_name.name]

    extra_provincials = []
    if furnishing.furnishing_name not in XPRO_FURNISHING_NAMES:
        # get response from get jurisdictions
        jurisdictions_response = get_jurisdictions(business_identifier, token)
        # get extra provincials array
        extra_provincials = get_extra_provincials(jurisdictions_response)

    # get template
    template = Path(
        f'{current_app.config.get("TEMPLATE_PATH")}/dissolution-involuntary-stage-1.md'
    ).read_text(encoding="utf-8")
    filled_template = substitute_template_parts(template, "md")
    # render template with vars
    jnja_template = Template(filled_template, autoescape=True)
    entity_dashboard_url = current_app.config.get("DASHBOARD_URL") + business_identifier
    number_description = "Registration" \
        if business.legal_type == Business.LegalTypes.EXTRA_PRO_A.value else "Incorporation"

    body = jnja_template.render(
        action=content["action"],
        attachment_name=content["attachment_name"],
        business_identifier=business_identifier,
        business_name=business_name,
        business_number=business.tax_id,
        delay_type=content["delay_type"],
        entity_dashboard_url=entity_dashboard_url,
        extra_provincials_display=format_extra_provincials(extra_provincials),
        next_step_action=content["next_step_action"],
        number_description=number_description,
        reason_description=content["reason_description"],
        reason_title=content["reason_title"]
    )

    # get recipients
    recipients = []
    recipients.append(furnishing.email)  # furnishing email

    recipients = list(set(recipients))
    recipients = ", ".join(filter(None, recipients)).strip()

    # get attachments
    pdfs = _get_pdfs(token, business, furnishing)

    subject = f"{business_name} - URGENT - Your business is in the process of being {content['action']}"

    return {
        "recipients": recipients,
        "requestBy": "BCRegistries@gov.bc.ca",
        "content": {
            "subject": subject,
            "body": body,
            "attachments": pdfs
        }
    }


def get_extra_provincials(response: dict) -> list[str]:
    """Get extra provincials name."""
    extra_provincials = []
    if response:
        jurisdictions = response.get("jurisdictions", [])
        for jurisdiction in jurisdictions:
            if jurisdiction.get("id") in NWPTA_JURISDICTION_IDS and (name := jurisdiction.get("name")):
                extra_provincials.append(name)
        extra_provincials.sort()
    return extra_provincials


def format_extra_provincials(extra_provincials: list[str]) -> str:
    """Format the extra provincial names into a display string."""
    if not extra_provincials:
        return ""
    if len(extra_provincials) == 1:
        return extra_provincials[0]
    if len(extra_provincials) == 2:
        return f"{extra_provincials[0]} and {extra_provincials[1]}"
    return f'{", ".join(extra_provincials[:-1])}, and {extra_provincials[-1]}'


def get_jurisdictions(identifier: str, token: str) -> dict:
    """Get jurisdictions call."""
    headers = {
        "Accept": "application/json",
        "Authorization": f"Bearer {token}"
    }

    response = requests.get(
        f'{current_app.config.get("LEGAL_API_URL")}/mras/{identifier}', headers=headers
    )
    if response.status_code != HTTPStatus.OK:
        return None
    try:
        return response.json()
    except Exception:
        current_app.logger.error("Failed to get MRAS response")
        return None


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

    filename = f'{FURNISHING_CONTENT[furnishing.furnishing_name.name]["attachment_name"]}.pdf'
    furnishing_pdf_encoded = base64.b64encode(furnishing_pdf.content)

    return [{
        "fileName": filename,
        "fileBytes": furnishing_pdf_encoded.decode("utf-8"),
        "fileUrl": "",
        "attachOrder": "1"
    }]
