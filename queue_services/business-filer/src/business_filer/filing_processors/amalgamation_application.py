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

from business_model.models import (
    AmalgamatingBusiness,
    Amalgamation,
    Business,
    Document,
    DocumentType,
    Filing,
    Party,
    Resolution,
)
from business_model.models.db import db
from dateutil.parser import parse

from business_filer.exceptions import QueueException
from business_filer.filing_meta import FilingMeta
from business_filer.filing_processors.filing_components import (
    aliases,
    business_info,
    filings,
    shares,
)
from business_filer.filing_processors.filing_components.offices import update_offices
from business_filer.filing_processors.filing_components.parties import update_parties


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
        elif identifier:
            # a business in COLIN that is not loaded in LEAR - validated against the COLIN
            # snapshot at submission; the colin sync write-back moves the corp to HAM
            amalgamating_business.colin_identifier = identifier
        else:
            raise QueueException(
                f"amalgamationApplication {filing_rec.id} has an amalgamating business "
                "with no identifier and no foreign jurisdiction.")

        amalgamation.amalgamating_businesses.append(amalgamating_business)


def dissolve_amalgamating_business(business: Business, filing_rec: Filing):
    """Dissolve amalgamating business."""
    business.dissolution_date = filing_rec.effective_date
    business.state = Business.State.HISTORICAL
    business.state_filing_id = filing_rec.id
    db.session.add(business)


def _update_cooperative(amalgamation_filing: dict, business: Business, filing: Filing):
    """Update the cooperative business with the cooperative specific information."""
    if cooperative_obj := amalgamation_filing.get("cooperative"):
        business.association_type = cooperative_obj.get("cooperativeAssociationType")
        document = Document()
        document.type = DocumentType.COOP_RULES.value
        document.file_key = cooperative_obj.get("rulesFileKey")
        document.business_id = business.id
        document.filing_id = filing.id
        business.documents.append(document)

        document = Document()
        document.type = DocumentType.COOP_MEMORANDUM.value
        document.file_key = cooperative_obj.get("memorandumFileKey")
        document.business_id = business.id
        document.filing_id = filing.id
        business.documents.append(document)

    _create_special_resolution(amalgamation_filing, business, filing)

    return business


def _create_special_resolution(amalgamation_filing: dict, business: Business, filing_rec: Filing):
    """Save the special resolution carried inline on a coop amalgamation."""
    if not amalgamation_filing.get("resolution"):
        return

    resolution = Resolution(
        resolution=amalgamation_filing.get("resolution"),
        resolution_type=Resolution.ResolutionType.SPECIAL.value,
        resolution_sub_type=filing_rec.filing_type
    )
    if signatory := amalgamation_filing.get("signatory"):
        party = Party(
            first_name=signatory.get("givenName", "").upper(),
            last_name=signatory.get("familyName", "").upper(),
            middle_initial=(signatory.get("additionalName", "") or "").upper(),
            title="",
            organization_name="",
            email="",
            identifier=""
        )
        resolution.party = party
    if amalgamation_filing.get("resolutionDate"):
        resolution.resolution_date = parse(amalgamation_filing.get("resolutionDate")).date()
    if amalgamation_filing.get("signingDate"):
        resolution.signing_date = parse(amalgamation_filing.get("signingDate")).date()
    business.resolutions.append(resolution)


def process(business: Business,  # noqa: PLR0912
            filing: dict,
            filing_rec: Filing,
            filing_meta: FilingMeta):
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
    corp_num = business_info.get_next_corp_num(business_info_obj["legalType"])
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
        # legal-api validation guarantees these sections mirror the primary/holding business
        missing = [section for section in ("offices", "parties", "shareStructure")
                   if not amalgamation_filing.get(section)]
        if not business_info_obj.get("legalName"):
            missing.append("nameRequest.legalName")
        if missing:
            raise QueueException(
                f"amalgamationApplication {filing_rec.id} short-form filing missing: {missing}")

    # Initial insert of the business record
    business = Business()
    business = business_info.update_business_info(corp_num, business, business_info_obj, filing_rec)
    business.state = Business.State.ACTIVE
    business.amalgamation.append(amalgamation)

    if business_info_obj["legalType"] == Business.LegalTypes.COOP.value:
        business = _update_cooperative(amalgamation_filing, business, filing_rec)

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
        shares.update_share_structure(
            business,
            share_structure,
            True  # for amalgamation, the primary/holding business must carry forward all resolution dates
        )

    if name_translations := amalgamation_filing.get("nameTranslations"):
        aliases.update_aliases(business, name_translations)

    if court_order := amalgamation_filing.get("courtOrder"):
        filings.create_court_order(filing_rec, court_order, filing_meta, business)

    # Update the filing json with identifier and founding date.
    amalgamation_json = copy.deepcopy(filing_rec.filing_json)
    amalgamation_json["filing"]["business"] = {}
    amalgamation_json["filing"]["business"]["identifier"] = business.identifier
    amalgamation_json["filing"]["business"]["legalType"] = business.legal_type
    amalgamation_json["filing"]["business"]["foundingDate"] = business.founding_date.isoformat()
    filing_rec._filing_json = amalgamation_json  # pylint: disable=protected-access; bypass to update filing data

    return business, filing_rec, filing_meta
