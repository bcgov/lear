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
from typing import Dict

from entity_queue_common.service_utils import QueueException
from legal_api.models import Business, Document, Filing
from legal_api.models.document import DocumentType
from legal_api.services import Flags, MinioService
from legal_api.services.pdf_service import RegistrarStampData

from entity_filer.filing_meta import FilingMeta
from entity_filer.filing_processors.filing_components import aliases, business_info, filings, shares
from entity_filer.filing_processors.filing_components.offices import update_offices
from entity_filer.filing_processors.filing_components.parties import update_parties
from entity_filer.utils import replace_file_with_certified_copy


def _update_cooperative(incorp_filing: Dict, business: Business, filing: Filing):
    cooperative_obj = incorp_filing.get('cooperative', None)
    if cooperative_obj:
        # create certified copy for rules document
        rules_file_key = cooperative_obj.get('rulesFileKey')
        rules_file = MinioService.get_file(rules_file_key)
        registrar_stamp_data = RegistrarStampData(business.founding_date, business.identifier)
        replace_file_with_certified_copy(rules_file.data, rules_file_key, registrar_stamp_data)

        business.association_type = cooperative_obj.get('cooperativeAssociationType')
        document = Document()
        document.type = DocumentType.COOP_RULES.value
        document.file_key = rules_file_key
        document.business_id = business.id
        document.filing_id = filing.id
        business.documents.append(document)

        # create certified copy for memorandum document
        memorandum_file_key = cooperative_obj.get('memorandumFileKey')
        memorandum_file = MinioService.get_file(memorandum_file_key)
        registrar_stamp_data = RegistrarStampData(business.founding_date, business.identifier)
        replace_file_with_certified_copy(memorandum_file.data, memorandum_file_key, registrar_stamp_data)

        document = Document()
        document.type = DocumentType.COOP_MEMORANDUM.value
        document.file_key = memorandum_file_key
        document.business_id = business.id
        document.filing_id = filing.id
        business.documents.append(document)

    return business


def process(business: Business,  # pylint: disable=too-many-branches,too-many-locals
            filing: Dict,
            filing_rec: Filing,
            filing_meta: FilingMeta,
            flags: Flags):  # pylint: disable=too-many-branches
    """Process the incoming incorporation filing."""
    # Extract the filing information for incorporation
    incorp_filing = filing.get('filing', {}).get('incorporationApplication')
    filing_meta.incorporation_application = {}

    if not incorp_filing:
        raise QueueException(f'IA legal_filing:incorporationApplication missing from {filing_rec.id}')
    if business:
        raise QueueException(f'Business Already Exist: IA legal_filing:incorporationApplication {filing_rec.id}')

    business_info_obj = incorp_filing.get('nameRequest')

    if filing_rec.colin_event_ids:
        corp_num = filing['filing']['business']['identifier']
    else:
        # Reserve the Corp Number for this entity
        corp_num = business_info.get_next_corp_num(business_info_obj['legalType'], flags)
        if not corp_num:
            raise QueueException(
                f'incorporationApplication {filing_rec.id} unable to get a business registration number.')

    # Initial insert of the business record
    business = Business()
    business = business_info.update_business_info(corp_num, business, business_info_obj, filing_rec)
    business = _update_cooperative(incorp_filing, business, filing_rec)
    business.state = Business.State.ACTIVE

    if nr_number := business_info_obj.get('nrNumber', None):
        filing_meta.incorporation_application = {**filing_meta.incorporation_application,
                                                 **{'nrNumber': nr_number,
                                                    'legalName': business_info_obj.get('legalName', None)}}

    if not business:
        raise QueueException(f'IA incorporationApplication {filing_rec.id}, Unable to create business.')

    if offices := incorp_filing['offices']:
        update_offices(business, offices)

    if parties := incorp_filing.get('parties'):
        update_parties(business, parties, filing_rec)

    if share_structure := incorp_filing.get('shareStructure'):
        shares.update_share_structure(business, share_structure)

    if name_translations := incorp_filing.get('nameTranslations'):
        aliases.update_aliases(business, name_translations)

    if court_order := incorp_filing.get('courtOrder'):
        filings.update_filing_court_order(filing_rec, court_order)

    if not filing_rec.colin_event_ids:
        # Update the filing json with identifier and founding date.
        ia_json = copy.deepcopy(filing_rec.filing_json)
        if not ia_json['filing'].get('business'):
            ia_json['filing']['business'] = {}
        ia_json['filing']['business']['identifier'] = business.identifier
        ia_json['filing']['business']['legalType'] = business.legal_type
        ia_json['filing']['business']['foundingDate'] = business.founding_date.isoformat()
        filing_rec._filing_json = ia_json  # pylint: disable=protected-access; bypass to update filing data
    return business, filing_rec, filing_meta
