# Copyright © 2022 Province of British Columbia
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
"""This module contains all of the Legal Filing specific processors.

Processors hold the logic to communicate with CRA.
"""
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

import requests
from flask import current_app, request
from jinja2 import Template
from legal_api.models import EntityRole, RequestTracker

from entity_bn.services.logging import structured_log


@dataclass
class Message:
    id: Optional[str] = None
    type: Optional[str] = None
    filing_id: Optional[str] = None
    identifier: Optional[str] = None
    request: Optional[str] = None
    business_number: Optional[str] = None


bn_note = (
    "Cannot inform CRA about this change before receiving "
    + "Business Number (BN15). Modify the "  # pylint: disable=invalid-name
    + "request xml by providing businessRegistrationNumber, businessProgramIdentifier and "
    + "businessProgramAccountReferenceNumber before resubmitting it."
)

program_type_code = {
    "SP": "113",
    "GP": "114",
    "BC": "100",
    "BEN": "100",
    "ULC": "125",
    "CC": "126",
}

document_sub_type = {
    RequestTracker.RequestType.CHANGE_PARTY: "102",
    RequestTracker.RequestType.CHANGE_NAME: "103",
    RequestTracker.RequestType.CHANGE_DELIVERY_ADDRESS: "107",
    RequestTracker.RequestType.CHANGE_MAILING_ADDRESS: "108",
}


def get_business_type_and_sub_type_code(
    legal_type: str, business_owned: bool, owner_legal_type: str
):
    """Get business_type and business_sub_type."""
    business_type = None
    business_sub_type = None

    if legal_type == "SP":
        if business_owned:  # Owned by an org
            if owner_legal_type in ["GP", "LP", "XP", "LL", "XL"]:
                business_type = "02"  # Partnership
                business_sub_type = "99"  # Business
            elif owner_legal_type in ["S", "XS"]:
                business_type = "03"  # Corporation
                business_sub_type = "09"  # Society
            elif owner_legal_type in ["CP", "XCP"]:
                business_type = "03"  # Corporation
                business_sub_type = "08"  # Association
            elif owner_legal_type in [
                "QC",
                "QD",
                "QB",
                "QE",
                "QA",
                "BC",
                "BEN",
                "A",
                "C",
                "LLC",
                "CUL",
                "ULC",
                "CC",
                "CCC",
                "FI",
                "PA",
            ]:
                business_type = "03"  # Corporation
                business_sub_type = "99"  # Business
            else:
                business_type = "99"  # Other
                business_sub_type = "99"  # Unknown
        else:  # Owned by an individual
            business_type = "01"  # Sole Proprietorship
            business_sub_type = "01"  # Sole Proprietor
    elif legal_type == "GP":
        business_type = "02"  # Partnership
        business_sub_type = "99"  # Business

    return business_type, business_sub_type


def build_input_xml(template_name, data):
    """Build input XML."""
    template = Path(
        f'{current_app.config.get("TEMPLATE_PATH")}/{template_name}.xml'
    ).read_text()
    jnja_template = Template(template, autoescape=True)
    return jnja_template.render(data)


def get_splitted_business_number(tax_id: str):
    """Split BN15 as required by CRA."""
    registration_number = ""
    program_identifier = ""
    program_account_reference_number = ""

    if tax_id and len(tax_id) == 15:
        registration_number = tax_id[0:9]
        program_identifier = tax_id[9:11]
        program_account_reference_number = tax_id[11:15]

    return {
        "businessRegistrationNumber": registration_number,
        "businessProgramIdentifier": program_identifier,
        "businessProgramAccountReferenceNumber": program_account_reference_number,
    }


def request_bn_hub(input_xml):
    """Get request to BN Hub."""
    try:
        url = current_app.config.get("BN_HUB_API_URL")
        username = current_app.config.get("BN_HUB_CLIENT_ID")
        secret = current_app.config.get("BN_HUB_CLIENT_SECRET")
        response = requests.get(
            url=url, params={"inputXML": input_xml}, auth=(username, secret)
        )
        return response.status_code, response.text
    except requests.exceptions.RequestException as err:
        structured_log(request, "ERROR", str(err))
        return None, str(err)


def get_owners_legal_type(entity_role: EntityRole):
    """Get owners entity type."""
    if not entity_role.is_related_colin_entity:
        return entity_role.related_entity.entity_type

    try:
        url = f'{current_app.config["SEARCH_API"]}/businesses/search/facets?\
                start=0&rows=20&categories=status:ACTIVE&query=value:{entity_role.related_colin_entity.identifier}'
        response = requests.get(url)
        response.raise_for_status()
        data = response.json()
        if results := data.get("searchResults", {}).get("results"):
            for entity in results:
                if (
                    entity.get("identifier")
                    == entity_role.related_colin_entity.identifier
                ):
                    return entity.get("legalType")
        return None
    except (requests.exceptions.RequestException, requests.exceptions.HTTPError) as err:
        structured_log(request, "ERROR", str(err))
        return None
