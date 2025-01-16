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
"""File processing rules and actions for the incorporation of a business."""
import copy
from contextlib import suppress
from typing import Dict

from legal_api.models import Business, Document, Filing, Jurisdiction
from legal_api.utils.legislation_datetime import LegislationDatetime

from ..filing_meta import FilingMeta
from .filing_components import aliases, business_info, business_profile, filings, shares
from .filing_components.offices import update_offices
from .filing_components.parties import update_parties

def create_foreign_jurisdiction(continuation_in: Dict,
                                business: Business,
                                filing: Filing,
                                filing_meta: FilingMeta):
    """Create jurisdiction and director affidavit document."""
    foreign_jurisdiction = continuation_in.get('foreignJurisdiction')

    jurisdiction = Jurisdiction()
    jurisdiction.country = foreign_jurisdiction.get('country')
    jurisdiction.region = foreign_jurisdiction.get('region')
    jurisdiction.legal_name = foreign_jurisdiction.get('legalName')
    jurisdiction.identifier = foreign_jurisdiction.get('identifier')
    incorporation_date = foreign_jurisdiction.get('incorporationDate')
    jurisdiction.incorporation_date = LegislationDatetime.as_utc_timezone_from_legislation_date_str(incorporation_date)
    jurisdiction.tax_id = foreign_jurisdiction.get('taxId')

    filing_meta.continuation_in = {
        **filing_meta.continuation_in,
        'country': jurisdiction.country,
        'region': jurisdiction.region
    }

    if expro_business := continuation_in.get('business'):
        jurisdiction.expro_identifier = expro_business.get('identifier')
        jurisdiction.expro_legal_name = expro_business.get('legalName')

    jurisdiction.filing_id = filing.id
    business.jurisdictions.append(jurisdiction)

    # if affidavit_file_key := foreign_jurisdiction.get('affidavitFileKey'):
    #     # only for CUL: AB and NS region
    #     document = Document()
    #     document.type = DocumentType.DIRECTOR_AFFIDAVIT.value
    #     document.file_key = affidavit_file_key
    #     document.filing_id = filing.id
    #     business.documents.append(document)

    #     filing_meta.continuation_in = {
    #         **filing_meta.continuation_in,
    #         'affidavitFileKey': affidavit_file_key,
    #     }


def process(business: Business,  # pylint: disable=too-many-branches,too-many-locals
            filing: Dict,
            filing_rec: Filing,
            filing_meta: FilingMeta):  # pylint: disable=too-many-branches
    """Process the incoming continuationIn filing."""
    # Extract the filing information for continuation in
    continuation_in = filing.get('filing', {}).get('continuationIn')
    filing_meta.continuation_in = {}

    if not continuation_in:
        print(f'legal_filing:continuationIn missing from {filing_rec.id}')
        raise Exception(f'legal_filing:continuationIn missing from {filing_rec.id}')
    if business:
        print(f'Business Already Exist: legal_filing:continuationIn {filing_rec.id}')
        raise Exception(f'Business Already Exist: legal_filing:continuationIn {filing_rec.id}')

    business_info_obj = continuation_in.get('nameRequest')
    corp_num = filing['filing']['business']['identifier']

    # Initial insert of the business record
    business = Business()
    business = business_info.update_business_info(corp_num, business, business_info_obj, filing_rec)
    business.state = Business.State.ACTIVE

    if nr_number := business_info_obj.get('nrNumber', None):
        filing_meta.continuation_in = {
            **filing_meta.continuation_in,
            'nrNumber': nr_number,
            'legalName': business_info_obj.get('legalName', None)
        }

    if not business:
        print(f'continuationIn {filing_rec.id}, Unable to create business.')
        raise Exception(f'continuationIn {filing_rec.id}, Unable to create business.')

    create_foreign_jurisdiction(continuation_in, business, filing_rec, filing_meta)
    # create_authorization_documents(continuation_in, business, filing_rec, filing_meta)

    if offices := continuation_in.get('offices'):
        update_offices(business, offices)

    if parties := continuation_in.get('parties'):
        update_parties(business, parties, filing_rec)

    if share_structure := continuation_in.get('shareStructure'):
        shares.update_share_structure(business, share_structure)

    if name_translations := continuation_in.get('nameTranslations'):
        aliases.update_aliases(business, name_translations)

    if court_order := continuation_in.get('courtOrder'):
        filings.update_filing_court_order(filing_rec, court_order)

    if not filing_rec.colin_event_ids:
        # Update the filing json with identifier and founding date.
        filing_json = copy.deepcopy(filing_rec.filing_json)
        if not filing_json['filing'].get('business'):
            filing_json['filing']['business'] = {}
        filing_json['filing']['business']['identifier'] = business.identifier
        filing_json['filing']['business']['legalType'] = business.legal_type
        filing_json['filing']['business']['foundingDate'] = business.founding_date.isoformat()
        filing_rec._filing_json = filing_json  # pylint: disable=protected-access; bypass to update filing data
    return business, filing_rec, filing_meta

def post_process(business: Business, filing: Filing):
    """Post processing activities for continuation in.

    THIS SHOULD NOT ALTER THE MODEL
    """
    with suppress(IndexError, KeyError, TypeError):
        if err := business_profile.update_business_profile(
            business,
            filing.json['filing']['continuationIn']['contactPoint']
        ):
            print(f'Queue Error: Update Business for filing:{filing.id}, error:{err}')
