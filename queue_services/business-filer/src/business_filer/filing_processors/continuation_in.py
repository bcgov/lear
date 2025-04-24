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
"""File processing rules and actions for the continuation in of a business."""
import copy

from business_model.models import Business, Document, DocumentType, Filing, Jurisdiction

from business_filer.common.legislation_datetime import LegislationDatetime
from business_filer.exceptions import QueueException
from business_filer.filing_meta import FilingMeta
from business_filer.filing_processors.filing_components import aliases, business_info, filings, shares
from business_filer.filing_processors.filing_components.offices import update_offices
from business_filer.filing_processors.filing_components.parties import update_parties
from business_filer.services import Flags


def create_foreign_jurisdiction(continuation_in: dict,
                                business: Business,
                                filing: Filing,
                                filing_meta: FilingMeta):
    """Create jurisdiction and director affidavit document."""
    foreign_jurisdiction = continuation_in.get("foreignJurisdiction")

    jurisdiction = Jurisdiction()
    jurisdiction.country = foreign_jurisdiction.get("country")
    jurisdiction.region = foreign_jurisdiction.get("region")
    jurisdiction.legal_name = foreign_jurisdiction.get("legalName")
    jurisdiction.identifier = foreign_jurisdiction.get("identifier")
    incorporation_date = foreign_jurisdiction.get("incorporationDate")
    jurisdiction.incorporation_date = LegislationDatetime.as_utc_timezone_from_legislation_date_str(incorporation_date)
    jurisdiction.tax_id = foreign_jurisdiction.get("taxId")

    filing_meta.continuation_in = {
        **filing_meta.continuation_in,
        "country": jurisdiction.country,
        "region": jurisdiction.region
    }

    if expro_business := continuation_in.get("business"):
        jurisdiction.expro_identifier = expro_business.get("identifier")
        jurisdiction.expro_legal_name = expro_business.get("legalName")

    jurisdiction.filing_id = filing.id
    business.jurisdictions.append(jurisdiction)

    if affidavit_file_key := foreign_jurisdiction.get("affidavitFileKey"):
        # only for CUL: AB and NS region
        document = Document()
        document.type = DocumentType.DIRECTOR_AFFIDAVIT.value
        document.file_key = affidavit_file_key
        document.filing_id = filing.id
        business.documents.append(document)

        filing_meta.continuation_in = {
            **filing_meta.continuation_in,
            "affidavitFileKey": affidavit_file_key,
        }


def create_authorization_documents(continuation_in: dict,
                                   business: Business,
                                   filing: Filing,
                                   filing_meta: FilingMeta):
    """Create authorization documents."""
    authorization_files = continuation_in.get("authorization", {}).get("files", [])
    files = []
    for file in authorization_files:
        document = Document()
        document.type = DocumentType.AUTHORIZATION_FILE.value
        document.file_key = file.get("fileKey")
        document.file_name = file.get("fileName")
        files.append({
            "fileKey": document.file_key,
            "fileName": document.file_name
        })
        document.filing_id = filing.id
        business.documents.append(document)

    filing_meta.continuation_in = {
        **filing_meta.continuation_in,
        "authorizationFiles": files,
    }


def process(business: Business,  # noqa: PLR0912
            filing: dict,
            filing_rec: Filing,
            filing_meta: FilingMeta,
            flags: Flags):
    """Process the incoming continuationIn filing."""
    # Extract the filing information for continuation in
    continuation_in = filing.get("filing", {}).get("continuationIn")
    filing_meta.continuation_in = {}

    if not continuation_in:
        raise QueueException(f"legal_filing:continuationIn missing from {filing_rec.id}")
    if business:
        raise QueueException(f"Business Already Exist: legal_filing:continuationIn {filing_rec.id}")

    business_info_obj = continuation_in.get("nameRequest")

    if filing_rec.colin_event_ids:
        corp_num = filing["filing"]["business"]["identifier"]
    else:
        # Reserve the Corp Number for this entity
        corp_num = business_info.get_next_corp_num(business_info_obj["legalType"], flags)
        if not corp_num:
            raise QueueException(
                f"continuationIn {filing_rec.id} unable to get a business registration number.")

    # Initial insert of the business record
    business = Business()
    business = business_info.update_business_info(corp_num, business, business_info_obj, filing_rec)
    business.state = Business.State.ACTIVE

    if nr_number := business_info_obj.get("nrNumber", None):
        filing_meta.continuation_in = {
            **filing_meta.continuation_in,
            "nrNumber": nr_number,
            "legalName": business_info_obj.get("legalName", None)
        }

    if not business:
        raise QueueException(f"continuationIn {filing_rec.id}, Unable to create business.")

    create_foreign_jurisdiction(continuation_in, business, filing_rec, filing_meta)
    create_authorization_documents(continuation_in, business, filing_rec, filing_meta)

    if offices := continuation_in.get("offices"):
        update_offices(business, offices)

    if parties := continuation_in.get("parties"):
        update_parties(business, parties, filing_rec)

    if share_structure := continuation_in.get("shareStructure"):
        shares.update_share_structure(business, share_structure)

    if name_translations := continuation_in.get("nameTranslations"):
        aliases.update_aliases(business, name_translations)

    if court_order := continuation_in.get("courtOrder"):
        filings.update_filing_court_order(filing_rec, court_order)

    if not filing_rec.colin_event_ids:
        # Update the filing json with identifier and founding date.
        filing_json = copy.deepcopy(filing_rec.filing_json)
        if not filing_json["filing"].get("business"):
            filing_json["filing"]["business"] = {}
        filing_json["filing"]["business"]["identifier"] = business.identifier
        filing_json["filing"]["business"]["legalType"] = business.legal_type
        filing_json["filing"]["business"]["foundingDate"] = business.founding_date.isoformat()
        filing_rec._filing_json = filing_json  # pylint: disable=protected-access; bypass to update filing data
    return business, filing_rec, filing_meta
