# Copyright © 2022 Province of British Columbia
#
# Licensed under the Apache License, Version 2.0 (the 'License');
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an 'AS IS' BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""Business checks for firms."""
from legal_api.models import Address, AlternateName, EntityRole, Filing, Office
from legal_api.models.business_common import BusinessCommon

from . import WARNING_MESSAGE_BASE  # noqa: I001
from . import BusinessWarningCodes  # noqa: I001
from . import BusinessWarningReferers  # noqa: I001
from . import BusinessWarnings  # noqa: I001
from . import get_address_business_warning  # noqa: I001


def check_business(business: any) -> list:
    """Check for missing business data."""
    result = []

    result.extend(check_office(business))
    result.extend(check_parties(business.entity_type, business))
    result.extend(check_start_date(business))

    return result


def check_start_date(business: any) -> list:
    """Check for business start date."""
    result = []
    if not business.start_date:
        result.append(
            {
                **WARNING_MESSAGE_BASE,
                "code": BusinessWarningCodes.NO_START_DATE,
                "message": "A start date is required.",
            }
        )
    return result


def check_office(business: any) -> list:
    """Check for missing office data."""
    result = []

    business_office = business.offices.filter(Office.office_type == "businessOffice").one_or_none()

    if not business_office:
        result.append(
            {
                **WARNING_MESSAGE_BASE,
                "code": BusinessWarningCodes.NO_BUSINESS_OFFICE,
                "message": "A business office is required.",
            }
        )
        return result

    addresses = business_office.addresses.all()

    mailing_address = next((x for x in addresses if x.address_type == "mailing"), None)
    result.extend(check_address(mailing_address, Address.MAILING, BusinessWarningReferers.BUSINESS_OFFICE))

    delivery_address = next((x for x in addresses if x.address_type == "delivery"), None)
    result.extend(check_address(delivery_address, Address.DELIVERY, BusinessWarningReferers.BUSINESS_OFFICE))

    return result


def check_parties(entity_type: str, business: any) -> list:
    """Check for missing parties data."""
    result = []

    if entity_type == BusinessCommon.EntityTypes.SOLE_PROP.value:
        result.extend(check_sp_parties(business))

        completing_party_filing = Filing.get_most_recent_legal_filing(business, "conversion")

        if not completing_party_filing:
            completing_party_filing = Filing.get_most_recent_legal_filing(business, "registration")

        result.extend(check_completing_party_for_filing(completing_party_filing))

    else:
        firm_entity_roles = business.entity_roles.filter(EntityRole.cessation_date.is_(None)).all()
        result.extend(check_gp_parties(firm_entity_roles))

        completing_party_filing = Filing.get_most_recent_legal_filing(business, "conversion")

        if not completing_party_filing:
            completing_party_filing = Filing.get_most_recent_legal_filing(business, "registration")

        result.extend(check_completing_party_for_filing(completing_party_filing))

    return result


def check_sp_parties(alternate_name: AlternateName) -> list:
    """Check for missing firm parties data."""
    result = []

    if not alternate_name.legal_entity and not alternate_name.colin_entity:
        result.append(
            {
                **WARNING_MESSAGE_BASE,
                "code": BusinessWarningCodes.NO_PROPRIETOR,
                "message": "A proprietor is required.",
            }
        )

    result.extend(check_sp_party(alternate_name))

    return result


def check_gp_parties(entity_roles: list) -> list:
    """Check for missing firm parties data."""
    result = []

    partner_count = 0

    for entity_role in entity_roles:
        if entity_role.role_type == EntityRole.RoleTypes.partner:
            partner_count += 1
            result.extend(check_gp_party(entity_role))

    if partner_count < 2:
        result.append(
            {
                **WARNING_MESSAGE_BASE,
                "code": BusinessWarningCodes.NO_PARTNER,
                "message": "2 partners are required.",
            }
        )

    return result


def check_completing_party_for_filing(filing: Filing) -> list:
    """Check for missing completing party data for conversion or registration filing."""
    result = []

    if not filing:
        result.append(
            {
                **WARNING_MESSAGE_BASE,
                "code": BusinessWarningCodes.NO_COMPLETING_PARTY,
                "message": "A completing party is required.",
            }
        )
        return result

    completing_party_role = filing.filing_entity_roles.filter(
        EntityRole.role_type == EntityRole.RoleTypes.completing_party
    ).one_or_none()

    if not completing_party_role:
        result.append(
            {
                **WARNING_MESSAGE_BASE,
                "code": BusinessWarningCodes.NO_COMPLETING_PARTY,
                "message": "A completing party is required.",
            }
        )
        return result

    result.extend(check_completing_party(completing_party_role))
    return result


# pylint: disable=too-many-branches;
def check_sp_party(alternate_name: AlternateName):
    """Check for missing firm party data."""
    result = []
    no_person_name_check_warning = False
    no_org_name_warning = False

    if alternate_name.is_owned_by_colin_entity:
        colin_entity = alternate_name.colin_entity
        if not colin_entity.organization_name:
            no_org_name_warning = True
        result.extend(
            check_address(alternate_name.owner_mailing_address, Address.MAILING, BusinessWarningReferers.BUSINESS_PARTY)
        )
    elif alternate_name.is_owned_by_legal_entity_person:
        legal_entity = alternate_name.legal_entity
        if not legal_entity.first_name and not legal_entity.last_name:
            no_person_name_check_warning = True
        result.extend(
            check_address(legal_entity.entity_mailing_address, Address.MAILING, BusinessWarningReferers.BUSINESS_PARTY)
        )
    elif alternate_name.is_owned_by_legal_entity_org:
        legal_entity = alternate_name.legal_entity
        if not legal_entity.legal_name:
            no_org_name_warning = True
        result.extend(
            check_address(alternate_name.owner_mailing_address, Address.MAILING, BusinessWarningReferers.BUSINESS_PARTY)
        )

    if no_person_name_check_warning:
        result.append(
            {
                **WARNING_MESSAGE_BASE,
                "code": BusinessWarningCodes.NO_PROPRIETOR_PERSON_NAME,
                "message": "Proprietor name is required.",
            }
        )
    if no_org_name_warning:
        result.append(
            {
                **WARNING_MESSAGE_BASE,
                "code": BusinessWarningCodes.NO_PROPRIETOR_ORG_NAME,
                "message": "Proprietor organization name is required.",
            }
        )

    return result


# pylint: disable=too-many-branches;
def check_gp_party(entity_role: EntityRole):
    """Check for missing firm party data."""
    result = []
    role = entity_role.role_type.replace("_", " ").title()
    no_person_name_check_warning = False
    no_org_name_warning = False

    if entity_role.is_related_colin_entity:
        colin_entity = entity_role.related_colin_entity
        if not colin_entity.organization_name:
            no_org_name_warning = True
        result.extend(
            check_address(colin_entity.mailing_address, Address.MAILING, BusinessWarningReferers.BUSINESS_PARTY)
        )
    elif entity_role.is_related_person:
        legal_entity = entity_role.related_entity
        if not legal_entity.first_name and not legal_entity.last_name:
            no_person_name_check_warning = True
        result.extend(
            check_address(legal_entity.entity_mailing_address, Address.MAILING, BusinessWarningReferers.BUSINESS_PARTY)
        )
    elif entity_role.is_related_organization:
        legal_entity = entity_role.related_entity
        if not legal_entity.legal_name:
            no_org_name_warning = True
        result.extend(
            check_address(legal_entity.entity_mailing_address, Address.MAILING, BusinessWarningReferers.BUSINESS_PARTY)
        )

    if no_person_name_check_warning:
        result.append(
            {
                **WARNING_MESSAGE_BASE,
                "code": BusinessWarningCodes.NO_PARTNER_PERSON_NAME,
                "message": f"{role} name is required.",
            }
        )
    if no_org_name_warning:
        result.append(
            {
                **WARNING_MESSAGE_BASE,
                "code": BusinessWarningCodes.NO_PARTNER_ORG_NAME,
                "message": f"{role} organization name is required.",
            }
        )

    return result


def check_completing_party(entity_role: EntityRole):
    """Check for missing completing party data."""
    result = []

    role = entity_role.role_type.replace("_", " ").title()

    if entity_role.is_filing_colin_entity:
        colin_entity = entity_role.related_colin_entity
        if not colin_entity.organization_name:
            result.append(
                {
                    **WARNING_MESSAGE_BASE,
                    "code": BusinessWarningCodes.NO_COMPLETING_PARTY_ORG_NAME,
                    "message": f"{role} organization name is required.",
                }
            )
        result.extend(
            check_address(colin_entity.mailing_address, Address.MAILING, BusinessWarningReferers.COMPLETING_PARTY)
        )
    elif entity_role.is_filing_related_person:
        legal_entity = entity_role.legal_entity
        if not legal_entity.first_name and not legal_entity.last_name:
            result.append(
                {
                    **WARNING_MESSAGE_BASE,
                    "code": BusinessWarningCodes.NO_COMPLETING_PARTY_PERSON_NAME,
                    "message": f"{role} name is required.",
                }
            )
        result.extend(
            check_address(
                legal_entity.entity_mailing_address, Address.MAILING, BusinessWarningReferers.COMPLETING_PARTY
            )
        )
    elif entity_role.is_filing_related_organization:
        legal_entity = entity_role.legal_entity
        if not legal_entity.legal_name:
            result.append(
                {
                    **WARNING_MESSAGE_BASE,
                    "code": BusinessWarningCodes.NO_COMPLETING_PARTY_ORG_NAME,
                    "message": f"{role} organization name is required.",
                }
            )
        result.extend(
            check_address(
                legal_entity.entity_mailing_address, Address.MAILING, BusinessWarningReferers.COMPLETING_PARTY
            )
        )

    return result


def check_address(address: Address, address_type: str, referer: BusinessWarningReferers) -> list:
    """Check for missing address data."""
    result = []

    if not address:
        result.append(get_address_business_warning(referer, address_type, BusinessWarnings.NO_ADDRESS))
        return result

    if not address.street:
        result.append(get_address_business_warning(referer, address_type, BusinessWarnings.NO_ADDRESS_STREET))
    if not address.city:
        result.append(get_address_business_warning(referer, address_type, BusinessWarnings.NO_ADDRESS_CITY))
    if not address.country:
        result.append(get_address_business_warning(referer, address_type, BusinessWarnings.NO_ADDRESS_COUNTRY))
    if not address.postal_code:
        result.append(get_address_business_warning(referer, address_type, BusinessWarnings.NO_ADDRESS_POSTAL_CODE))

    if referer == BusinessWarningReferers.BUSINESS_OFFICE and address_type == Address.DELIVERY and not address.region:
        result.append(get_address_business_warning(referer, address_type, BusinessWarnings.NO_ADDRESS_REGION))

    return result
