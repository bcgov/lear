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

from business_model.models import AmalgamatingBusiness, Amalgamation, Business, Filing, OfficeType, PartyRole
from business_model.models.db import db

from business_filer.exceptions import QueueException
from business_filer.filing_meta import FilingMeta
from business_filer.filing_processors.filing_components import (
    JSON_ROLE_CONVERTER,
    aliases,
    business_info,
    filings,
    shares,
)
from business_filer.filing_processors.filing_components.offices import update_offices
from business_filer.filing_processors.filing_components.parties import update_parties
from business_filer.services import Flags


def create_amalgamating_businesses(amalgamation_filing: dict, amalgamation: Amalgamation, filing_rec: Filing):
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
        elif business := Business.find_by_identifier(identifier):
            amalgamating_business.business_id = business.id
            dissolve_amalgamating_business(business, filing_rec)

        amalgamation.amalgamating_businesses.append(amalgamating_business)


def dissolve_amalgamating_business(business: Business, filing_rec: Filing):
    """Dissolve amalgamating business."""
    business.dissolution_date = filing_rec.effective_date
    business.state = Business.State.HISTORICAL
    business.state_filing_id = filing_rec.id
    db.session.add(business)


def process(business: Business,  # pylint: disable=too-many-branches, too-many-locals
            filing: dict,
            filing_rec: Filing,
            filing_meta: FilingMeta,
            flags: Flags):
    """Process the incoming amalgamation application filing."""
    # Extract the filing information for amalgamation
    amalgamation_filing = filing.get("filing", {}).get("amalgamationApplication")
    filing_meta.amalgamation_application = {}

    if not amalgamation_filing:
        raise QueueException(
            f"AmalgamationApplication legal_filing:amalgamationApplication missing from {filing_rec.id}")
    if business:
        raise QueueException(
            f"Business Already Exist: AmalgamationApplication legal_filing:amalgamationApplication {filing_rec.id}")

    business_info_obj = amalgamation_filing.get("nameRequest")

    # Reserve the Corp Number for this entity
    corp_num = business_info.get_next_corp_num(business_info_obj["legalType"], flags)
    if not corp_num:
        raise QueueException(
            f"amalgamationApplication {filing_rec.id} unable to get a business amalgamationApplication number.")

    amalgamation = Amalgamation()
    amalgamation.filing_id = filing_rec.id
    amalgamation.amalgamation_type = amalgamation_filing.get("type")
    amalgamation.amalgamation_date = filing_rec.effective_date
    amalgamation.court_approval = bool(amalgamation_filing.get("courtApproval"))
    create_amalgamating_businesses(amalgamation_filing, amalgamation, filing_rec)
    if amalgamation.amalgamation_type in [Amalgamation.AmalgamationTypes.horizontal.name,
                                          Amalgamation.AmalgamationTypes.vertical.name]:
        # Include/Replace legal_name, director, office and shares from holding/primary business (won't be a foreign)
        amalgamating_business = next(x for x in amalgamation.amalgamating_businesses
                                     if x.role in [AmalgamatingBusiness.Role.holding.name,
                                                   AmalgamatingBusiness.Role.primary.name])
        primary_or_holding_business = Business.find_by_internal_id(amalgamating_business.business_id)

        business_info_obj["legalName"] = primary_or_holding_business.legal_name

        _set_parties(primary_or_holding_business, filing_rec, amalgamation_filing)
        _set_offices(primary_or_holding_business, amalgamation_filing)
        _set_shares(primary_or_holding_business, amalgamation_filing)

    # Initial insert of the business record
    business = Business()
    business = business_info.update_business_info(corp_num, business, business_info_obj, filing_rec)
    business.state = Business.State.ACTIVE
    business.amalgamation.append(amalgamation)

    if nr_number := business_info_obj.get("nrNumber", None):
        filing_meta.amalgamation_application = {**filing_meta.amalgamation_application,
                                                "nrNumber": nr_number,
                                                   "legalName": business_info_obj.get("legalName", None)}

    if not business:
        raise QueueException(f"amalgamationApplication {filing_rec.id}, Unable to create business.")

    if offices := amalgamation_filing.get("offices"):
        update_offices(business, offices)

    if parties := amalgamation_filing.get("parties"):
        update_parties(business, parties, filing_rec)

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
    amalgamation_json["filing"]["business"]["legalType"] = business.legal_type
    amalgamation_json["filing"]["business"]["foundingDate"] = business.founding_date.isoformat()
    filing_rec._filing_json = amalgamation_json  # pylint: disable=protected-access; bypass to update filing data

    return business, filing_rec, filing_meta


def _set_parties(primary_or_holding_business, filing_rec, amalgamation_filing):
    parties = []
    active_directors = PartyRole.get_active_directors(primary_or_holding_business.id,
                                                      filing_rec.effective_date.date())
    # copy director
    for director in active_directors:
        director_json = director.json
        director_json["roles"] = [{
            "roleType": "Director",
            "appointmentDate": filing_rec.effective_date.isoformat()
        }]

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
        if comp_party_role := next((x for x in party_info.get("roles")
                                    if JSON_ROLE_CONVERTER.get(x["roleType"].lower(), "")
                                    == PartyRole.RoleTypes.COMPLETING_PARTY.value), None):
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
    business_dates = [item.resolution_date.isoformat() for item in primary_or_holding_business.resolutions]
    if business_dates:
        amalgamation_filing["shareStructure"]["resolutionDates"] = business_dates
