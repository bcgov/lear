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
"""Manages the parties and party roles for a LegalEntity."""
from __future__ import annotations

import datetime
from typing import Dict, List, Optional, Tuple

from business_model import Address, ColinEntity, EntityRole, Filing, LegalEntity

from entity_filer import db
from entity_filer.exceptions import BusinessException, ErrorCode, get_error_message
from entity_filer.filing_processors.filing_components import create_address, create_role, legal_entity_info, merge_party


def update_parties(
    legal_entity: LegalEntity,
    parties_structure: Dict,
    filing: Filing,
    delete_existing=True,
) -> Optional[List]:
    """Manage the party and entity roles for a legal_entity.

    Assumption: The structure has already been validated, upon submission.

    Other errors are recorded and will be managed out of band.
    """
    if not legal_entity:
        # if nothing is passed in, we don't care and it's not an error
        return None

    err = []

    if parties_structure:
        if delete_existing:
            try:
                delete_parties(legal_entity)
            except:  # noqa:E722 pylint: disable=bare-except; catch all exceptions
                err.append(
                    {
                        "error_code": "FILER_UNABLE_TO_DELETE_PARTY_ROLES",
                        "error_message": f"Filer: unable to delete party roles for :'{legal_entity.identifier}'",
                    }
                )
                return err

        try:
            for party_info in parties_structure:
                party = merge_party(legal_entity_id=legal_entity.id, party_info=party_info, create=False)
                for role_type in party_info.get("roles"):
                    role_str = role_type.get("roleType", "").lower()
                    role = {
                        "roleType": role_str,
                        "appointmentDate": role_type.get("appointmentDate", None),
                        "cessationDate": role_type.get("cessationDate", None),
                    }
                    party_role = create_role(party=party, role_info=role)
                    if party_role.role in [
                        EntityRole.RoleTypes.completing_party.value,
                        EntityRole.RoleTypes.incorporator.value,
                        EntityRole.RoleTypes.applicant.value,
                    ]:
                        filing.filing_party_roles.append(party_role)
                    else:
                        legal_entity.party_roles.append(party_role)
        except KeyError:
            err.append(
                {
                    "error_code": "FILER_UNABLE_TO_SAVE_PARTIES",
                    "error_message": f"Filer: unable to save new parties for :'{legal_entity.identifier}'",
                }
            )
    return err


def delete_parties(legal_entity: LegalEntity):
    """Delete the entity_roles for a legal_entity."""
    if existing_party_roles := legal_entity.entity_roles.all():
        for role in existing_party_roles:
            legal_entity.entity_roles.remove(role)


def merge_all_parties(legal_entity: LegalEntity, filing: Filing, parties: dict) -> [dict] | None:
    """Merge all parties supplied and return a dict of errors, or None

    This top level method does 4 things:
    1. Adds and links parties to filing oriented roles (eg. completing party)
    2. Updates existing parties and their roles, they have an id
    3. Add new parties and their roles, they have no id (eg. directors)
    4. Remove representing parties that are no longer referenced.
       Set has directors, so remove existing directors NOT in the set.
    """
    memoize_existing_director_ids = []
    memoize_existing_partners = []
    errors = []

    if not parties.get("parties"):
        return [{"error": f"no parties to process for filing:{filing.id}"}]

    for party_dict in parties["parties"]:
        # Setup the party (legal_entity) we are working with
        # and get the address to use for the filing roles being assigned

        # if we don't have a party type, bail as this is an error
        # we can't recover from
        if not (party_type := party_dict.get("officer", {}).get("partyType")):
            status_code = ErrorCode.GENERAL_UNRECOVERABLE_ERROR
            raise BusinessException(
                status_code=status_code,
                error=get_error_message(status_code, **{"filing_id": filing.id}),
            )

        # if party_type == 'organization':
        #     all_roles = [role for role in party_dict.get('roles',{}).get('roleType')]
        #     valid_org_role = EntityRole.valid_org_roles
        #     at_least_one = any(i in all_roles for i in valid_org_role)

        # Get or Create the party
        party_le = None
        if (
            (party_identifier := party_dict.get("officer", {}).get("identifier"))
            and (
                (party_le := LegalEntity.find_by_identifier(party_identifier))
                or (party_le := ColinEntity.find_by_identifier(party_identifier))
            )
        ) or (
            (not party_identifier)
            and (party_id := party_dict.get("officer", {}).get("id"))
            and (isinstance(party_id, int) or party_id.isnumeric())
            and ((party_le := LegalEntity.find_by_id(party_id)) or (party_le := ColinEntity.find_by_id(party_id)))
        ):
            existing_party = True

        # until data conversion, we create ColinEntity if needed
        elif party_type in ["person", "organization"]:
            party_le = create_entity_with_addresses(party_dict)
            existing_party = False

        else:
            status_code = ErrorCode.GENERAL_UNRECOVERABLE_ERROR
            raise BusinessException(
                status_code=status_code,
                error=get_error_message(status_code, **{"filing_id": filing.id}),
            )

        # An existing person can have a different set of addresses
        # for this set of roles
        if existing_party and party_type == "person":
            update_person_info(party_le, party_dict)
            delivery_address = get_address_for_filing(
                party_le.entity_delivery_address, party_dict.get("deliveryAddress")
            )
            mailing_address = get_address_for_filing(party_le.entity_mailing_address, party_dict.get("mailingAddress"))
        else:
            # New People and Orgs use the attached addresses
            if isinstance(party_le, ColinEntity):
                delivery_address = party_le.delivery_address
                mailing_address = party_le.mailing_address
            else:
                delivery_address = party_le.entity_delivery_address
                mailing_address = party_le.entity_mailing_address

        if not party_dict.get("roles"):
            errors.append({"error": f"no valid roles assigned to party:{party_le}"})
            continue

        for role in party_dict["roles"]:
            if role_type := role.get("roleType"):
                match role_type:
                    case "Director" if party_type == "person":
                        # memoize_existing_director_ids.append(party_le.id)
                        memoize_existing_director_ids.append(party_le)

                        merge_entity_role_for_director(
                            party_le=party_le,
                            filing=filing,
                            delivery_address=delivery_address,
                            mailing_address=mailing_address,
                            base_entity=legal_entity,
                            role_dict=role,
                        )

                    case "Completing Party":
                        # add to the filing
                        merge_entity_role_to_filing(
                            party_le,
                            filing,
                            EntityRole.RoleTypes.completing_party,
                            delivery_address,
                            mailing_address,
                        )

                    case "Incorporator":
                        merge_entity_role_to_filing(
                            party_le,
                            filing,
                            EntityRole.RoleTypes.incorporator,
                            delivery_address,
                            mailing_address,
                            legal_entity,
                            role,
                        )

                    case "Applicant" if party_type == "person":
                        merge_entity_role_to_filing(
                            party_le,
                            filing,
                            map_schema_role_to_enum(role_type),
                            delivery_address,
                            mailing_address,
                            legal_entity,
                            role,
                        )

                    case "Custodian" | "Liquidator":
                        merge_entity_role_to_filing(
                            party_le,
                            filing,
                            map_schema_role_to_enum(role_type),
                            delivery_address,
                            mailing_address,
                            legal_entity,
                            role,
                        )

                    case "Partner":
                        memoize_existing_partners.append(party_le)
                        merge_entity_role_to_filing(
                            party_le,
                            filing,
                            map_schema_role_to_enum(role_type),
                            delivery_address,
                            mailing_address,
                            legal_entity,
                            role,
                        )

                    case "Proprietor":
                        print("Proprietor role being skipped.")

                    case _:
                        errors.append({"warning": f"role: {role_type} not assigned to party:{party_le}"})
                        print(f"no matching roles for party: {party_type} and role: {role_type}")

    if memoize_existing_director_ids:
        delete_non_memoized_entity_role(
            legal_entity, filing, memoize_existing_director_ids, EntityRole.RoleTypes.director
        )

    if memoize_existing_partners:
        delete_non_memoized_entity_role(legal_entity, filing, memoize_existing_partners, EntityRole.RoleTypes.partner)

    return errors if len(errors) > 0 else None


def merge_entity_role_to_filing(
    party_le: any,
    filing: Filing,
    role: EntityRole.RoleTypes,
    delivery_address: Address,
    mailing_address: Address,
    base_entity: LegalEntity = None,
    role_dict: dict = None,
) -> EntityRole:
    """Add the EntityRole to the filing."""
    if not (
        base_entity
        and (
            entity_role := EntityRole.find_by_party_id_and_role(
                party_id=party_le.id,
                legal_entity_id=base_entity.id,
                role=role,
            )
        )
    ):
        entity_role = EntityRole()

    # Blind updates
    entity_role.change_filing_id = filing.id

    if not entity_role.id:
        entity_role.filing_id = filing.id
        entity_role.appointment_date = filing.effective_date
        # entity_role.delivery_address_id=delivery_address.id
        # entity_role.legal_entity_id=base_entity.id if base_entity else None
        # entity_role.mailing_address_id=mailing_address.id
        # entity_role.related_entity_id=party_le.id
        entity_role.delivery_address = delivery_address
        entity_role.mailing_address = mailing_address
        entity_role.legal_entity = base_entity if base_entity else None
        entity_role.role_type = role

        if isinstance(party_le, ColinEntity):
            entity_role.related_colin_entity = party_le
        else:
            entity_role.related_entity = party_le

        filing.filing_entity_roles.append(entity_role)

    if role_dict and (cessation_date := role_dict.get("cessationDate")):
        filing_id = entity_role.filing_id
        entity_role.cessation_date = datetime.datetime.fromisoformat(cessation_date)
        filing.save()
        filing.filing_entity_roles.remove(entity_role)
        entity_role.filing_id = filing_id
        entity_role.delete()

    # filing.save()
    return entity_role


def merge_entity_role_for_director(
    party_le: LegalEntity,
    base_entity: LegalEntity,
    filing: Filing,
    delivery_address: Address,
    mailing_address: Address,
    role_dict: dict,
) -> EntityRole:
    """Add the EntityRole to the filing."""
    if not (
        entity_role := EntityRole.find_by_party_id_and_role(
            party_id=party_le.id,
            legal_entity_id=base_entity.id,
            role=EntityRole.RoleTypes.director,
        )
    ):
        entity_role = EntityRole()

    # Blind updates
    entity_role.appointment_date = role_dict.get("appointmentDate") or filing.effective_date
    entity_role.change_filing_id = filing.id
    # entity_role.delivery_address_id=delivery_address.id
    # entity_role.legal_entity_id=base_entity.id
    # entity_role.mailing_address_id=mailing_address.id
    # entity_role.related_entity_id=party_le.id
    entity_role.delivery_address = delivery_address
    entity_role.role_type = EntityRole.RoleTypes.director
    entity_role.legal_entity = base_entity
    entity_role.mailing_address = mailing_address
    entity_role.related_entity = party_le

    if not entity_role.id:
        filing.filing_entity_roles.append(entity_role)
        filing.save()
    else:
        entity_role.save()

    if cessation_date := role_dict.get("cessationDate"):
        entity_role.cessation_date = datetime.datetime.fromisoformat(cessation_date)
        # delete saves and then deletes to push this into the history
        entity_role.delete()

    return entity_role


def create_entity_with_addresses(party_dict) -> LegalEntity:
    """Create a new LegalEntity from the party dict."""
    if not (party_type := party_dict["officer"].get("partyType")):
        raise Exception

    if party_type == "person":
        person_reg_num = legal_entity_info.get_next_corp_num("P")
        new_party = LegalEntity(
            first_name=party_dict["officer"].get("firstName", "").upper(),
            last_name=party_dict["officer"].get("lastName", "").upper(),
            middle_initial=party_dict["officer"]
            .get("middleInitial", party_dict["officer"].get("middleName", ""))
            .upper(),
            email=party_dict["officer"].get("email"),
            _entity_type=LegalEntity.EntityTypes.PERSON,
            identifier=person_reg_num,
        )
    elif party_type == "organization":
        new_party = ColinEntity(
            organization_name=party_dict["officer"].get("organizationName", "").upper(),
            identifier=party_dict["officer"].get("identifier", "").upper(),
            email=party_dict["officer"].get("email"),
        )
    else:
        raise Exception()

    if party_dict.get("mailingAddress"):
        mailing_address = Address(
            street=party_dict["mailingAddress"]["streetAddress"],
            city=party_dict["mailingAddress"]["addressCity"],
            country="CA",
            postal_code=party_dict["mailingAddress"]["postalCode"],
            region=party_dict["mailingAddress"]["addressRegion"],
            delivery_instructions=party_dict["mailingAddress"].get("deliveryInstructions", ""),
        )
        # mailing_address.save()
        # new_party.mailing_address_id = mailing_address.id
        if isinstance(new_party, LegalEntity):
            new_party.entity_mailing_address = mailing_address
        else:
            new_party.mailing_address = mailing_address

    if party_dict.get("deliveryAddress"):
        delivery_address = Address(
            street=party_dict["deliveryAddress"]["streetAddress"],
            city=party_dict["deliveryAddress"]["addressCity"],
            country="CA",
            postal_code=party_dict["deliveryAddress"]["postalCode"],
            region=party_dict["deliveryAddress"]["addressRegion"],
            delivery_instructions=party_dict["deliveryAddress"].get("deliveryInstructions", ""),
        )
        # delivery_address.save()
        # new_party.delivery_address_id = delivery_address.id
        if isinstance(new_party, LegalEntity):
            new_party.entity_delivery_address = delivery_address
        else:
            new_party.delivery_address = delivery_address

    return new_party


def get_address_for_filing(party_address: Address, address_dict: dict) -> Address:
    """Return either the address on record, or the address in the filing."""
    if (
        party_address
        and party_address.street == address_dict["streetAddress"]
        and party_address.city == address_dict["addressCity"]
        and party_address.country == address_dict["addressCountry"]
        and party_address.postal_code == address_dict["postalCode"]
        and party_address.region == address_dict["addressRegion"]
        and party_address.delivery_instructions == address_dict.get("deliveryInstructions", "")
    ):
        return party_address

    new_address = Address(
        street=address_dict["streetAddress"],
        city=address_dict["addressCity"],
        country=address_dict["addressCountry"],
        postal_code=address_dict["postalCode"],
        region=address_dict["addressRegion"],
        delivery_instructions=address_dict.get("deliveryInstructions", ""),
    )
    # new_address.save()
    return new_address


def delete_non_memoized_entity_role(
    legal_entity: LegalEntity, filing: Filing, keep_list, role: EntityRole.RoleTypes
) -> []:
    """Delete EntityRoles for role not in the keep_list."""
    candidates = EntityRole.get_parties_by_role(legal_entity.id, role)

    for candidate in candidates:
        if candidate.related_entity in keep_list:
            continue

        candidate.cessation_date = filing.effective_date
        candidate.change_filing_id = filing.id
        candidate.delete()

    return None


def get_or_create_party(party_dict: dict, filing: Filing):
    party_le = None
    party_type = party_dict.get("officer", {}).get("partyType")

    if (
        (party_identifier := party_dict.get("officer", {}).get("identifier"))
        and (
            (party_le := LegalEntity.find_by_identifier(party_identifier))
            or (party_le := ColinEntity.find_by_identifier(party_identifier))
        )
    ) or (
        (not party_identifier)
        and (party_id := party_dict.get("officer", {}).get("id"))
        and (isinstance(party_id, int) or party_id.isnumeric())
        and ((party_le := LegalEntity.find_by_id(party_id)) or (party_le := ColinEntity.find_by_id(party_id)))
    ):
        existing_party = True

    # until data conversion, we create ColinEntity if needed
    elif party_type in ["person", "organization"]:
        party_le = create_entity_with_addresses(party_dict)
        existing_party = False

    else:
        status_code = ErrorCode.GENERAL_UNRECOVERABLE_ERROR
        raise BusinessException(
            status_code=status_code,
            error=get_error_message(status_code, **{"filing_id": filing.id}),
        )

    # An existing person can have a different set of addresses
    # for this set of roles
    if existing_party and party_type == "person":
        update_person_info(party_le, party_dict)
        delivery_address = get_address_for_filing(party_le.entity_delivery_address, party_dict.get("deliveryAddress"))
        mailing_address = get_address_for_filing(party_le.entity_mailing_address, party_dict.get("mailingAddress"))
    else:
        # New People and Orgs use the attached addresses
        if isinstance(party_le, ColinEntity):
            delivery_address = party_le.delivery_address
            mailing_address = party_le.mailing_address
        else:
            delivery_address = party_le.entity_delivery_address
            mailing_address = party_le.entity_mailing_address

    return party_le, delivery_address, mailing_address


def update_person_info(party_le, party_dict):
    party_le.first_name = party_dict["officer"].get("firstName", "").upper()
    party_le.last_name = party_dict["officer"].get("lastName", "").upper()
    party_le.middle_initial = (
        party_dict["officer"].get("middleInitial", party_dict["officer"].get("middleName", "")).upper()
    )
    party_le.email = party_dict["officer"].get("email")


def map_schema_role_to_enum(role_type: str) -> EntityRole.RoleTypes:
    """Map schema_role name to Entity RoleTypes."""
    ERT = EntityRole.RoleTypes
    match role_type:
        case "Applicant":
            return ERT.applicant

        case "Completing Party":
            return ERT.completing_party

        case "Custodian":
            return ERT.custodian

        case "Director":
            return ERT.director

        case "Incorporator":
            return ERT.incorporator

        case "Liquidator":
            return ERT.liquidator

        case "Partner":
            return ERT.partner

        case "Proprietor":
            return ERT.applicant

        case _:
            return None
