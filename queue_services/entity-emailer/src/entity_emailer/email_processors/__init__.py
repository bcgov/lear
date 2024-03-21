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
from typing import Tuple

import requests
from flask import current_app, request
from legal_api.models import Filing, LegalEntity
from legal_api.utils.legislation_datetime import LegislationDatetime

from entity_emailer.services.logging import structured_log


def get_filing_info(filing_id: str) -> Tuple[Filing, dict, dict, str, str]:
    """Get filing info for the email."""
    filing = Filing.find_by_id(filing_id)
    if filing.legal_entity_id:
        business = LegalEntity.find_by_internal_id(filing.legal_entity_id)
        business_json = business.json()
    else:
        business_json = (filing.json)["filing"].get("business")

    filing_date = datetime.fromisoformat(filing.filing_date.isoformat())
    leg_tmz_filing_date = LegislationDatetime.as_legislation_timezone(filing_date)
    hour = leg_tmz_filing_date.strftime("%I").lstrip("0")
    am_pm = leg_tmz_filing_date.strftime("%p").lower()
    leg_tmz_filing_date = leg_tmz_filing_date.strftime(f"%B %d, %Y at {hour}:%M {am_pm} Pacific time")

    effective_date = datetime.fromisoformat(filing.effective_date.isoformat())
    leg_tmz_effective_date = LegislationDatetime.as_legislation_timezone(effective_date)
    hour = leg_tmz_effective_date.strftime("%I").lstrip("0")
    am_pm = leg_tmz_effective_date.strftime("%p").lower()
    leg_tmz_effective_date = leg_tmz_effective_date.strftime(f"%B %d, %Y at {hour}:%M {am_pm} Pacific time")

    return filing, business_json, leg_tmz_filing_date, leg_tmz_effective_date


def get_recipients(option: str, filing_json: dict, token: str = None, filing_type: str = None) -> str:
    """Get the recipients for the email output."""
    recipients = ""
    filing_type = filing_type if filing_type else "incorporationApplication"
    if filing_json["filing"].get(filing_type):
        recipients = filing_json["filing"][filing_type]["contactPoint"]["email"]
        if option in [Filing.Status.PAID.value, "bn"] and filing_json["filing"]["header"]["name"] == filing_type:
            parties = filing_json["filing"][filing_type].get("parties")
            comp_party_email = None
            for party in parties:
                for role in party["roles"]:
                    if role["roleType"] == "Completing Party" and (comp_party_email := party["officer"].get("email")):
                        recipients = f"{recipients}, {comp_party_email}"
                        break
    else:
        identifier = filing_json["filing"]["business"]["identifier"]
        if not identifier[:2] == "CP":
            # only add recipients if not coop
            recipients = get_recipient_from_auth(identifier, token)

    return recipients


def get_recipient_from_auth(identifier: str, token: str) -> str:
    """Get the recipients for the email output from auth."""
    headers = {"Accept": "application/json", "Authorization": f"Bearer {token}"}

    contact_info = requests.get(f'{current_app.config.get("AUTH_URL")}/entities/{identifier}', headers=headers)
    contacts = contact_info.json()["contacts"]

    if not contacts:
        structured_log(
            request,
            "ERROR",
            f"Queue Error: No email in business {identifier} profile to send output to.",
        )
        raise Exception  # pylint: disable=broad-exception-raised

    return contacts[0]["email"]


def get_user_email_from_auth(user_name: str, token: str) -> str:
    """Get user email from auth."""
    user_info = get_user_from_auth(user_name, token)
    contacts = user_info.json()["contacts"]

    if not contacts:
        return user_info.get("email")  # idir user

    return contacts[0]["email"]


def get_user_from_auth(user_name: str, token: str) -> requests.Response:
    """Get user from auth."""
    headers = {"Accept": "application/json", "Authorization": f"Bearer {token}"}

    user_info = requests.get(f'{current_app.config.get("AUTH_URL")}/users/{user_name}', headers=headers)
    return user_info


def substitute_template_parts(template_code: str) -> str:
    """Substitute template parts in main template.

    Template parts are marked by [[partname.html]] in templates.

    This functionality is restricted by:
    - markup must be exactly [[partname.html]] and have no extra spaces around file name
    - template parts can only be one level deep, ie: this rudimentary framework does not handle nested template
    parts. There is no recursive search and replace.
    """
    template_parts = [
        "business-dashboard-link",
        "business-dashboard-link-alt",
        "business-info",
        "business-information",
        "reg-business-info",
        "cra-notice",
        "nr-footer",
        "footer",
        "header",
        "initiative-notice",
        "logo",
        "pdf-notice",
        "style",
        "divider",
        "20px",
        "whitespace-16px",
        "whitespace-24px",
    ]

    # substitute template parts - marked up by [[filename]]
    for template_part in template_parts:
        template_part_code = Path(f'{current_app.config.get("TEMPLATE_PATH")}/common/{template_part}.html').read_text()
        template_code = template_code.replace("[[{}.html]]".format(template_part), template_part_code)

    return template_code
