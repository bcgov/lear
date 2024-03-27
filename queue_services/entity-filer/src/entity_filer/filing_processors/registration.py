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
"""File processing rules and actions for the registration of a business."""
import copy
from contextlib import suppress
from http import HTTPStatus
from typing import Dict

import dpath
import sentry_sdk
from business_model import AlternateName, BusinessCommon, Filing, LegalEntity, RegistrationBootstrap

# from entity_filer.exceptions import DefaultException
from entity_filer.exceptions import DefaultException
from entity_filer.filing_meta import FilingMeta
from entity_filer.filing_processors.filing_components import filings, legal_entity_info
from entity_filer.filing_processors.filing_components.alternate_name import get_partnership_name
from entity_filer.filing_processors.filing_components.offices import update_offices
from entity_filer.filing_processors.filing_components.parties import get_or_create_party, merge_all_parties

# from legal_api.services.bootstrap import AccountService
from entity_filer.utils.legislation_datetime import LegislationDatetime


def update_affiliation(business: LegalEntity, filing: Filing):
    """Create an affiliation for the business and remove the bootstrap."""
    try:
        bootstrap = RegistrationBootstrap.find_by_identifier(filing.temp_reg)
        pass_code = legal_entity_info.get_firm_affiliation_passcode(  # noqa F841; remove this when below is done
            business.id
        )

        nr_number = filing.filing_json.get("filing").get("registration", {}).get("nameRequest", {}).get("nrNumber")
        details = {  # noqa F841; remove this comment when below is done
            "bootstrapIdentifier": bootstrap.identifier,
            "identifier": business.identifier,
            "nrNumber": nr_number,
        }
        # TODO Replace with call to Queue

    #     rv = AccountService.create_affiliation(
    #         account=bootstrap.account,
    #         business_registration=business.identifier,
    #         business_name=business.legal_name,
    #         corp_type_code=business.legal_type,
    #         pass_code=pass_code,
    #         details=details
    #     )

    #     if rv not in (HTTPStatus.OK, HTTPStatus.CREATED):
    #         deaffiliation = AccountService.delete_affiliation(bootstrap.account, business.identifier)
    #         sentry_sdk.print(
    #             f'Queue Error: Unable to affiliate business:{business.identifier} for filing:{filing.id}',
    #             level='error'
    #         )
    #     else:
    #         # update the bootstrap to use the new business identifier for the name
    #         bootstrap_update = AccountService.update_entity(
    #             business_registration=bootstrap.identifier,
    #             business_name=business.identifier,
    #             corp_type_code='RTMP'
    #         )

    #     if rv not in (HTTPStatus.OK, HTTPStatus.CREATED) \
    #             or ('deaffiliation' in locals() and deaffiliation != HTTPStatus.OK)\
    #             or ('bootstrap_update' in locals() and bootstrap_update != HTTPStatus.OK):
    #         raise DefaultException
    except Exception as err:  # pylint: disable=broad-except; note out any exception, but don't fail the call
        sentry_sdk.print(
            f"Queue Error: Affiliation error for filing:{filing.id}, with err:{err}",
            level="error",
        )


def process(
    business: any,  # pylint: disable=too-many-branches
    filing: Dict,
    filing_rec: Filing,
    filing_meta: FilingMeta,
):  # pylint: disable=too-many-branches
    """Process the incoming registration filing."""
    # Extract the filing information for registration
    if business:
        raise DefaultException(f"Business Already Exist: Registration legal_filing:registration {filing_rec.id}")

    if not (registration_filing := filing.get("filing", {}).get("registration")):
        raise DefaultException(f"Registration legal_filing:registration missing from {filing_rec.id}")

    entity_type = registration_filing.get("nameRequest", {}).get("legalType")
    if entity_type not in (
        BusinessCommon.EntityTypes.SOLE_PROP,
        BusinessCommon.EntityTypes.PARTNERSHIP,
    ):
        raise DefaultException(f"{filing_rec.id} has no valid legatype for a Registration.")

    filing_meta.registration = {}

    business_info_obj = registration_filing.get("nameRequest")

    # Reserve the Corp Number for this entity
    if not (firm_reg_num := legal_entity_info.get_next_corp_num("FM")):
        raise DefaultException(f"registration {filing_rec.id} unable to get a Firm registration number.")

    match entity_type:
        case BusinessCommon.EntityTypes.SOLE_PROP:
            # Get or create LE
            business, alternate_name = merge_sp_registration(firm_reg_num, filing, filing_rec)

        case BusinessCommon.EntityTypes.PARTNERSHIP:
            # Create Partnership
            business, alternate_name = merge_partnership_registration(
                firm_reg_num, filing, filing_rec, registration_filing
            )

        case _:
            # Default and failed
            # Based on the above checks, this should never happen
            raise DefaultException(f"registration {filing_rec.id} had no valid Firm type.")

    if nr_number := business_info_obj.get("nrNumber", None):
        # TODO check how this is getting used, may need operating name?
        filing_meta.registration = {
            **filing_meta.registration,
            **{
                "nrNumber": nr_number,
                "legalName": business_info_obj.get("legalName", None),
            },
        }

    if offices := registration_filing["offices"]:
        update_offices(alternate_name, offices)
        if entity_type == BusinessCommon.EntityTypes.PARTNERSHIP:
            update_offices(business, offices)

    if parties := registration_filing.get("parties"):
        merge_all_parties(business, filing_rec, {"parties": parties})

    # update court order, if any is present
    with suppress(IndexError, KeyError, TypeError):
        court_order_json = dpath.util.get(filing, "/registration/courtOrder")
        filings.update_filing_court_order(filing_rec, court_order_json)

    # Update the filing json with identifier and founding date.
    registration_json = copy.deepcopy(filing_rec.filing_json)
    registration_json["filing"]["business"] = {}
    registration_json["filing"]["business"]["identifier"] = alternate_name.identifier
    registration_json["filing"]["registration"]["business"]["identifier"] = alternate_name.identifier
    registration_json["filing"]["business"]["legalType"] = alternate_name.entity_type
    # registration_json['filing']['business']['foundingDate'] = business.founding_date.isoformat()
    filing_rec._filing_json = registration_json  # pylint: disable=protected-access; bypass to update filing data

    return business, alternate_name, filing_rec, filing_meta


def post_process(business: LegalEntity, filing: Filing):
    """Post processing activities for registration.

    THIS SHOULD NOT ALTER THE MODEL
    """
    pass


def merge_partnership_registration(
    registration_num: str,
    filing: Dict,
    filing_rec: Filing,
    registration_filing: dict,
):
    # Initial insert of the business record
    business_info_obj = registration_filing.get("nameRequest")
    business = LegalEntity()
    business = legal_entity_info.update_legal_entity_info(registration_num, business, business_info_obj, filing_rec)
    business.start_date = LegislationDatetime.as_utc_timezone_from_legislation_date_str(
        registration_filing.get("startDate")
    )
    business.founding_date = filing_rec.effective_date
    business.tax_id = registration_filing.get("business", {}).get("taxId", None)
    business._legal_name = get_partnership_name(registration_filing.get("parties"))
    business.state = BusinessCommon.State.ACTIVE

    alternate_name = AlternateName(
        bn15=registration_filing.get("business", {}).get("taxId", None),
        change_filing_id=filing_rec.id,
        end_date=registration_filing.get("endDate", None),
        identifier=registration_num,
        name=registration_filing.get("nameRequest", {}).get("legalName"),
        name_type=AlternateName.NameType.DBA,
        start_date=filing_rec.effective_date,
        business_start_date=business.start_date,
        state=BusinessCommon.State.ACTIVE,
    )

    if naics_dict := registration_filing.get("business", {}).get("naics"):
        set_naics(business, naics_dict)
        set_naics(alternate_name, naics_dict)

    business.alternate_names.append(alternate_name)

    return business, alternate_name


def merge_sp_registration(registration_num: str, filing: Dict, filing_rec: Filing) -> LegalEntity:
    # find or create the LE for the SP Owner

    if not (parties_dict := filing["filing"]["registration"]["parties"]):
        raise DefaultException(f"Missing parties in the SP registration for filing:{filing_rec.id}")

    # Find the Proprietor
    proprietor = None
    for party in parties_dict:
        for role in party.get("roles"):
            if role.get("roleType") == "Proprietor":
                proprietor_dict = party
                break
        if proprietor_dict:
            break

    if not proprietor_dict:
        raise DefaultException(f"No Proprietor in the SP registration for filing:{filing_rec.id}")

    proprietor, delivery_address, mailing_address = get_or_create_party(proprietor_dict, filing_rec)
    if not proprietor:
        raise DefaultException(f"No Proprietor in the SP registration for filing:{filing_rec.id}")

    operating_name = filing.get("filing", {}).get("registration", {}).get("nameRequest", {}).get("legalName")
    if start := filing.get("filing", {}).get("registration", {}).get("startDate"):
        business_start_date = LegislationDatetime.as_utc_timezone_from_legislation_date_str(start)
    elif filing.effective_date:
        business_start_date = filing.effective_date
    else:
        business_start_date = LegislationDatetime.now()

    if filing_rec.effective_date:
        start_date = filing_rec.effective_date
    else:
        start_date = LegislationDatetime.now()

    if isinstance(proprietor, LegalEntity) and proprietor.entity_type == BusinessCommon.EntityTypes.PERSON:
        delivery_address_id = None
        mailing_address_id = None
    else:
        delivery_address_id = delivery_address.id if delivery_address else None
        mailing_address_id = mailing_address.id if mailing_address else None

    tax_id = filing.get("filing", {}).get("business", {}).get("taxId", None)

    if (
        isinstance(proprietor, LegalEntity)
        and proprietor.entity_type == BusinessCommon.EntityTypes.PERSON
        and not proprietor.tax_id
    ):
        proprietor.tax_id = tax_id

    alternate_name = AlternateName(
        identifier=registration_num,
        name_type=AlternateName.NameType.DBA,
        change_filing_id=filing_rec.id,
        end_date=None,
        name=operating_name,
        start_date=start_date,
        business_start_date=business_start_date,
        delivery_address_id=delivery_address_id,
        mailing_address_id=mailing_address_id,
        bn15=tax_id,
        email=proprietor.email,
        state=BusinessCommon.State.ACTIVE,
    )

    if naics_dict := filing.get("filing", {}).get("registration", {}).get("business", {}).get("naics"):
        set_naics(alternate_name, naics_dict)

    proprietor.alternate_names.append(alternate_name)

    return proprietor, alternate_name


def set_naics(business: any, naics_dict: dict):
    """Set the NAICS fields for a business."""
    business.naics_code = naics_dict["naicsCode"]
    business.naics_description = naics_dict["naicsDescription"]
