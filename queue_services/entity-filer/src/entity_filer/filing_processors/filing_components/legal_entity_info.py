# Copyright © 2020 Province of British Columbia
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
"""Manages the type of Business."""
from datetime import datetime
from tokenize import String
from typing import Dict

import requests
from business_model import EntityRole, Filing, LegalEntity, LegalEntityIdentifier, LegalEntityType
from flask import current_app
from flask_babel import _ as babel  # noqa: N813

# from legal_api.services import NaicsService


class NaicsService:
    @staticmethod
    def find_by_code(naics_code: str):
        return None


def set_corp_type(legal_entity: LegalEntity, legal_entity_info: Dict) -> Dict:
    """Set the legal type of the legal_entity."""
    if not legal_entity:
        return {"error": babel("Business required before type can be set.")}

    try:
        entity_type = legal_entity_info.get("legalType")
        if entity_type:
            legal_entity.entity_type = entity_type
    except (IndexError, KeyError, TypeError):
        return {"error": babel("A valid legal type must be provided.")}

    return None


def set_association_type(legal_entity: LegalEntity, association_type: String) -> Dict:
    """Set the association type of legal_entity."""
    if not legal_entity:
        return {"error": babel("Business required before type can be set.")}

    try:
        cooperative_association_type = association_type
        if cooperative_association_type:
            legal_entity.association_type = cooperative_association_type
    except (IndexError, KeyError, TypeError):
        return {"error": babel("A valid association type must be provided.")}

    return None


def set_legal_name(corp_num: str, legal_entity: LegalEntity, legal_entity_info: Dict):
    """Set the legal_name in the legal_entity object."""
    if legal_name := legal_entity_info.get("legalName", None):
        legal_entity.legal_name = legal_name
    else:
        entity_type = legal_entity_info.get("legalType", None)
        numbered_legal_name_suffix = LegalEntity.BUSINESSES[entity_type]["numberedBusinessNameSuffix"]
        legal_entity.legal_name = f"{corp_num[2:]} {numbered_legal_name_suffix}"


def update_legal_entity_info(corp_num: str, legal_entity: LegalEntity, legal_entity_info: Dict, filing: Filing):
    """Format and update the legal_entity entity from incorporation filing."""
    if corp_num and legal_entity and legal_entity_info and filing:
        set_legal_name(corp_num, legal_entity, legal_entity_info)
        legal_entity.identifier = corp_num
        legal_entity.entity_type = legal_entity_info.get("legalType", None)
        legal_entity.founding_date = filing.effective_date
        legal_entity.last_coa_date = filing.effective_date
        legal_entity.last_cod_date = filing.effective_date
        return legal_entity
    return None


def update_naics_info(legal_entity: LegalEntity, naics: Dict):
    """Update naics info."""
    # TODO update NAICS info
    legal_entity.naics_code = naics.get("naicsCode")
    if legal_entity.naics_code:
        # TODO: Uncomment next 2 lines when find_by_code implemented and delete "pass"
        # naics_structure = NaicsService.find_by_code(legal_entity.naics_code)
        # legal_entity.naics_key = naics_structure["naicsKey"]
        pass
    else:
        legal_entity.naics_code = None
        legal_entity.naics_key = None
    legal_entity.naics_description = naics.get("naicsDescription")


def get_next_corp_num(entity_type: str):
    """Retrieve the next available sequential corp-num from Lear or fallback to COLIN."""
    # this gets called if the new services are generating the LegalEntity.identifier.
    if entity_type in LegalEntityType:
        if business_type := LegalEntityType.get_enum_by_value(entity_type):
            return LegalEntityIdentifier.next_identifier(business_type)
        return None

    # legacy LegalEntity.Identifier generation
    try:
        # TODO: update this to grab the legal 'class' after legal classes have been defined in lear
        if entity_type in (
            LegalEntity.EntityTypes.BCOMP.value,
            LegalEntity.EntityTypes.BC_ULC_COMPANY.value,
            LegalEntity.EntityTypes.BC_CCC.value,
            LegalEntity.EntityTypes.COMP.value,
        ):
            business_type = "BC"
        else:
            business_type = entity_type
        resp = requests.post(f'{current_app.config["COLIN_API"]}/{business_type}')
    except requests.exceptions.ConnectionError:
        current_app.print(f'Failed to connect to {current_app.config["COLIN_API"]}')
        return None

    if resp.status_code == 200:
        new_corpnum = int(resp.json()["corpNum"])
        if new_corpnum and new_corpnum <= 9999999:
            # TODO: Fix endpoint
            return f"{business_type}{new_corpnum:07d}"
    return None


def get_firm_affiliation_passcode(legal_entity_id: int):
    """Return a firm passcode for a given legal_entity identifier."""
    pass_code = None
    end_date = datetime.utcnow().date()
    party_roles = EntityRole.get_entity_roles(legal_entity_id, end_date)

    if len(party_roles) == 0:
        return pass_code

    party = party_roles[0].related_entity_id

    if party.party_type == "organization":
        pass_code = party.organization_name
    else:
        pass_code = party.last_name + ", " + party.first_name
        if hasattr(party, "middle_initial") and party.middle_initial:
            pass_code = pass_code + " " + party.middle_initial

    return pass_code
