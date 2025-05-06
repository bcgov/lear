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
"""Email processing rules and actions for Name Request before expiry, expiry, renewal, upgrade."""
from __future__ import annotations

from datetime import datetime
from enum import Enum
from http import HTTPStatus
from pathlib import Path

from flask import current_app
from jinja2 import Template

from business_emailer.email_processors import substitute_template_parts
from business_emailer.services.namex import NameXService
from business_model.utils.legislation_datetime import LegislationDatetime


class Option(Enum):
    """NR notification option."""

    BEFORE_EXPIRY = "before-expiry"
    EXPIRED = "expired"
    RENEWAL = "renewal"
    UPGRADE = "upgrade"
    REFUND = "refund"


def __is_modernized(legal_type):
    modernized_list = ["GP", "DBA", "FR", "CP", "BC"]
    return legal_type in modernized_list


def __is_colin(legal_type):
    colin_list = ["CR", "UL", "CC", "XCR", "XUL", "RLC"]
    return legal_type in colin_list


def _is_society(legal_type):
    society_list = ["SO", "XSO"]
    return legal_type in society_list


def __get_instruction_group(legal_type):
    if __is_modernized(legal_type):
        return "modernized"
    if __is_colin(legal_type):
        return "colin"
    if _is_society(legal_type):
        return "so"
    return ""


def process(email_info: dict, option) -> dict:  # pylint: disable-msg=too-many-locals
    """
    Build the email for Name Request notification.

    valid values of option: Option
    """
    current_app.logger.debug("NR %s notification: %s", option, email_info)
    nr_number = email_info["identifier"]

    nr_response = NameXService.query_nr_number(nr_number)
    if nr_response.status_code != HTTPStatus.OK:
        current_app.logger.error("Failed to get nr info for name request: %s", nr_number)
        return {}

    nr_data = nr_response.json()

    expiration_date = ""
    if nr_data["expirationDate"]:
        exp_date = datetime.fromisoformat(nr_data["expirationDate"])
        exp_date_tz = LegislationDatetime.as_legislation_timezone(exp_date)
        expiration_date = LegislationDatetime.format_as_report_string(exp_date_tz)

    refund_value = ""
    if option == Option.REFUND.value:
        refund_value = email_info.get("request", {}).get("refundValue", None)

    legal_name = ""
    for n_item in nr_data["names"]:
        if n_item["state"] in ("APPROVED", "CONDITION"):
            legal_name = n_item["name"]
            break

    name_request_url = current_app.config.get("NAME_REQUEST_URL")
    decide_business_url = current_app.config.get("DECIDE_BUSINESS_URL")
    corp_online_url = current_app.config.get("COLIN_URL")
    form_page_url = current_app.config.get("CORP_FORMS_URL")
    societies_url = current_app.config.get("SOCIETIES_URL")

    file_name_suffix = option.upper()
    if option == Option.BEFORE_EXPIRY.value and "entity_type_cd" in nr_data:
        legal_type = nr_data["entity_type_cd"]
        group = __get_instruction_group(legal_type)
        if group:
            instruction_group = "-" + group
            file_name_suffix += instruction_group.upper()

    template = Path(f'{current_app.config.get("TEMPLATE_PATH")}/NR-{file_name_suffix}.html').read_text()
    filled_template = substitute_template_parts(template)

    # render template with vars
    mail_template = Template(filled_template, autoescape=True)
    html_out = mail_template.render(
        nr_number=nr_number,
        expiration_date=expiration_date,
        legal_name=legal_name,
        refund_value=refund_value,
        name_request_url=name_request_url,
        decide_business_url=decide_business_url,
        corp_online_url=corp_online_url,
        form_page_url=form_page_url,
        societies_url=societies_url
    )

    # get recipients
    recipients = nr_data["applicants"]["emailAddress"]
    if not recipients:
        return {}

    subjects = {
        Option.BEFORE_EXPIRY.value: "Expiring Soon",
        Option.EXPIRED.value: "Expired",
        Option.RENEWAL.value: "Confirmation of Renewal",
        Option.UPGRADE.value: "Confirmation of Upgrade",
        Option.REFUND.value: "Refund request confirmation"
    }

    return {
        "recipients": recipients,
        "requestBy": "BCRegistries@gov.bc.ca",
        "content": {
            "subject": f"{nr_number} - {subjects[option]}",
            "body": f"{html_out}",
            "attachments": []
        }
    }
