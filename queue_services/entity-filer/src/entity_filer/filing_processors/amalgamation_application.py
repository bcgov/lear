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
"""File processing rules and actions for the amalgamation application of a business."""
import copy
from contextlib import suppress
from http import HTTPStatus
from typing import Dict

import sentry_sdk
from entity_queue_common.service_utils import QueueException
from legal_api import db
from legal_api.models import (
    AmalgamatingBusiness,
    Amalgamation,
    Filing,
    LegalEntity,
    OfficeType,
    PartyRole,
    RegistrationBootstrap,
)
from legal_api.services.bootstrap import AccountService

from entity_filer.exceptions import DefaultException
from entity_filer.filing_meta import FilingMeta
from entity_filer.filing_processors.filing_components import (
    JSON_ROLE_CONVERTER,
    aliases,
    business_info,
    business_profile,
    filings,
    legal_entity_info,
    shares,
)
from entity_filer.filing_processors.filing_components.offices import update_offices
from entity_filer.filing_processors.filing_components.parties import merge_all_parties

# from legal_api.services.bootstrap import AccountService


def update_affiliation(business: LegalEntity, filing: Filing):
    """Create an affiliation for the business and remove the bootstrap."""
    # TODO remove all of this
    pass
    # try:
    #     bootstrap = RegistrationBootstrap.find_by_identifier(filing.temp_reg)

    #     nr_number = (filing.filing_json
    #                  .get("filing")
    #                  .get("amalgamationApplication", {})
    #                  .get("nameRequest", {})
    #                  .get("nrNumber"))
    #     details = {
    #         "bootstrapIdentifier": bootstrap.identifier,
    #         "identifier": business.identifier,
    #         "nrNumber": nr_number
    #     }

    #     rv = AccountService.create_affiliation(
    #         account=bootstrap.account,
    #         business_registration=business.identifier,
    #         business_name=business.legal_name,
    #         corp_type_code=business.legal_type,
    #         details=details
    #     )

    #     if rv not in (HTTPStatus.OK, HTTPStatus.CREATED):
    #         deaffiliation = AccountService.delete_affiliation(bootstrap.account, business.identifier)
    #         sentry_sdk.capture_message(
    #             f"Queue Error: Unable to affiliate business:{business.identifier} for filing:{filing.id}",
    #             level="error"
    #         )
    #     else:
    #         update the bootstrap to use the new business identifier for the name
    #         bootstrap_update = AccountService.update_entity(
    #             business_registration=bootstrap.identifier,
    #             business_name=business.identifier,
    #             corp_type_code="ATMP"
    #         )

    #     if rv not in (HTTPStatus.OK, HTTPStatus.CREATED) \
    #             or ("deaffiliation" in locals() and deaffiliation != HTTPStatus.OK)\
    #             or ("bootstrap_update" in locals() and bootstrap_update != HTTPStatus.OK):
    #         raise DefaultException
    # except Exception as err:  # pylint: disable=broad-except; note out any exception, but don"t fail the call
    #     sentry_sdk.capture_message(
    #         f"Queue Error: Affiliation error for filing:{filing.id}, with err:{err}",
    #         level="error"
    #     )


def create_amalgamating_businesses(amalgamation_filing: Dict, amalgamation: Amalgamation, filing_rec: Filing):
    """Create amalgamating businesses."""
    amalgamating_businesses_json = amalgamation_filing.get("amalgamatingBusinesses", [])
    for amalgamating_business_json in amalgamating_businesses_json:
        amalgamating_business = AmalgamatingBusiness()
        amalgamating_business.role = amalgamating_business_json.get("role")
        identifier = amalgamating_business_json.get("identifier")
        if foreign_jurisdiction := amalgamating_business_json.get("foreignJurisdiction"):
            amalgamating_business.foreign_identifier = identifier
            amalgamating_business.foreign_name = amalgamating_business_json.get("legalName")
            amalgamating_business.foreign_jurisdiction = foreign_jurisdiction.get("country").upper()
            if region := foreign_jurisdiction.get("region"):
                amalgamating_business.foreign_jurisdiction_region = region.upper()
        elif business := LegalEntity.find_by_identifier(identifier):
            amalgamating_business.legal_entity_id = business.id
            dissolve_amalgamating_business(business, filing_rec)

        amalgamation.amalgamating_businesses.append(amalgamating_business)


def dissolve_amalgamating_business(business: LegalEntity, filing_rec: Filing):
    """Dissolve amalgamating business."""
    business.dissolution_date = filing_rec.effective_date
    business.state = LegalEntity.State.HISTORICAL
    business.state_filing_id = filing_rec.id
    db.session.add(business)


def process(
    business: LegalEntity,  # pylint: disable=too-many-branches, too-many-locals
    filing: Dict,
    filing_rec: Filing,
    filing_meta: FilingMeta,
):
    """Process the incoming amalgamation application filing."""
    # Extract the filing information for amalgamation
    amalgamation_filing = filing.get("filing", {}).get("amalgamationApplication")
    filing_meta.amalgamation_application = {}
    amalgamation = Amalgamation()

    if not amalgamation_filing:
        raise DefaultException(
            f"AmalgamationApplication legal_filing:amalgamationApplication missing from {filing_rec.id}"
        )
    if business:
        raise DefaultException(
            f"LegalEntity Already Exist: AmalgamationApplication legal_filing:amalgamationApplication {filing_rec.id}"
        )

    business_info_obj = amalgamation_filing.get("nameRequest")

    # Reserve the Corp Number for this entity
    corp_num = legal_entity_info.get_next_corp_num(business_info_obj["legalType"])
    if not corp_num:
        raise DefaultException(
            f"amalgamationApplication {filing_rec.id} unable to get a business amalgamationApplication number."
        )

    # Initial insert of the business record
    business = LegalEntity()
    business = legal_entity_info.update_legal_entity_info(corp_num, business, business_info_obj, filing_rec)
    business.state = LegalEntity.State.ACTIVE

    amalgamation.filing_id = filing_rec.id
    amalgamation_type = amalgamation_filing.get("type")
    amalgamation.amalgamation_type = amalgamation_type
    amalgamation.amalgamation_date = filing_rec.effective_date
    amalgamation.court_approval = bool(amalgamation_filing.get("courtApproval"))
    create_amalgamating_businesses(amalgamation_filing, amalgamation, filing_rec)
    business.amalgamation.append(amalgamation)

    if nr_number := business_info_obj.get("nrNumber", None):
        filing_meta.amalgamation_application = {
            **filing_meta.amalgamation_application,
            **{"nrNumber": nr_number, "legalName": business_info_obj.get("legalName", None)},
        }

    if not business:
        raise DefaultException(f"amalgamationApplication {filing_rec.id}, Unable to create business.")

    if amalgamation_type in [
        Amalgamation.AmalgamationTypes.horizontal.name,
        Amalgamation.AmalgamationTypes.vertical.name,
    ]:
        # Include/Replace director, office and shares by finding holding or primary business (won't be a foreign)
        amalgamating_business = next(
            x
            for x in amalgamation.amalgamating_businesses
            if x.role in [AmalgamatingBusiness.Role.holding.name, AmalgamatingBusiness.Role.primary.name]
        )
        primary_or_holding_business = LegalEntity.find_by_internal_id(amalgamating_business.business_id)

        _set_parties(primary_or_holding_business, filing_rec, amalgamation_filing)
        _set_offices(primary_or_holding_business, amalgamation_filing)
        _set_shares(primary_or_holding_business, amalgamation_filing)

    if offices := amalgamation_filing.get("offices"):
        update_offices(business, offices)

    if parties := amalgamation_filing.get("parties"):
        merge_all_parties(business, filing_rec, {"parties": parties})

    if share_structure := amalgamation_filing.get("shareStructure"):
        shares.update_share_structure(business, share_structure)

    if name_translations := amalgamation_filing.get("nameTranslations"):
        aliases.update_aliases(business, name_translations)

    if court_order := amalgamation_filing.get("courtOrder"):
        filings.update_filing_court_order(filing_rec, court_order)

    # Update the filing json with identifier and founding date.
    amalgamation_json = copy.deepcopy(filing_rec.filing_json)
    amalgamation_json["filing"]["business"] = {}
    amalgamation_json["filing"]["business"]["identifier"] = business.identifier
    amalgamation_json["filing"]["business"]["legalType"] = business.entity_type
    amalgamation_json["filing"]["business"]["foundingDate"] = business.founding_date.isoformat()
    filing_rec._filing_json = amalgamation_json  # pylint: disable=protected-access; bypass to update filing data

    return business, filing_rec, filing_meta


def _set_parties(primary_or_holding_business, filing_rec, amalgamation_filing):
    parties = []
    active_directors = PartyRole.get_active_directors(primary_or_holding_business.id, filing_rec.effective_date.date())
    # copy director
    for director in active_directors:
        director_json = director.json
        director_json["roles"] = [{"roleType": "Director", "appointmentDate": filing_rec.effective_date.isoformat()}]

        # cleanup director json
        del director_json["officer"]["id"]
        del director_json["role"]
        del director_json["appointmentDate"]
        if "cessationDate" in director_json:
            del director_json["cessationDate"]
        if "deliveryAddress" in director_json:
            del director_json["deliveryAddress"]["id"]
        if "mailingAddress" in director_json:
            del director_json["mailingAddress"]["id"]

        parties.append(director_json)

    # copy completing party from filing json
    for party_info in amalgamation_filing.get("parties"):
        if comp_party_role := next(
            (
                x
                for x in party_info.get("roles")
                if JSON_ROLE_CONVERTER.get(x["roleType"].lower(), "") == PartyRole.RoleTypes.COMPLETING_PARTY.value
            ),
            None,
        ):
            party_info["roles"] = [comp_party_role]  # override roles to have only completing party
            parties.append(party_info)
            break
    amalgamation_filing["parties"] = parties


def _set_offices(primary_or_holding_business, amalgamation_filing):
    # copy offices
    offices = {}
    officelist = primary_or_holding_business.offices.all()
    for i in officelist:
        if i.office_type in [OfficeType.REGISTERED, OfficeType.RECORDS]:
            offices[i.office_type] = {}
            for address in i.addresses:
                address_json = address.json
                del address_json["id"]
                offices[i.office_type][f"{address.address_type}Address"] = address_json
    amalgamation_filing["offices"] = offices


def _set_shares(primary_or_holding_business, amalgamation_filing):
    # copy shares
    share_classes = []
    for share_class in primary_or_holding_business.share_classes.all():
        share_class_json = share_class.json
        del share_class_json["id"]
        for series in share_class_json.get("series", []):
            del series["id"]
        share_classes.append(share_class_json)
    amalgamation_filing["shareStructure"] = {"shareClasses": share_classes}


def post_process(business: LegalEntity, filing: Filing):
    """Post processing activities for amalgamation application.

    THIS SHOULD NOT ALTER THE MODEL
    """
    # with suppress(IndexError, KeyError, TypeError):
    #     if err := business_profile.update_business_profile(
    #         business,
    #         filing.json["filing"]["amalgamationApplication"]["contactPoint"]
    #     ):
    #         sentry_sdk.capture_message(
    #             f"Queue Error: Update LegalEntity for filing:{filing.id}, error:{err}",
    #             level="error")
