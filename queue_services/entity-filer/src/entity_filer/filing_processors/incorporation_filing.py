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
from http import HTTPStatus
from typing import Dict

import sentry_sdk
from business_model import AlternateName, BusinessCommon, Document, Filing, LegalEntity, RegistrationBootstrap
from business_model.models.document import DocumentType

from entity_filer.exceptions import DefaultException
from entity_filer.filing_meta import FilingMeta
from entity_filer.filing_processors.filing_components import aliases
from entity_filer.filing_processors.filing_components import alternate_name as alternate_name_info
from entity_filer.filing_processors.filing_components import filings, legal_entity_info, shares
from entity_filer.filing_processors.filing_components.offices import update_offices
from entity_filer.filing_processors.filing_components.parties import merge_all_parties

# from legal_api.services.bootstrap import AccountService
# from legal_api.services.minio import MinioService
# from legal_api.services.pdf_service import RegistrarStampData


# from entity_filer.utils import replace_file_with_certified_copy


def update_affiliation(business: LegalEntity, filing: Filing):
    """Create an affiliation for the business and remove the bootstrap."""
    # TODO remove all of this
    pass
    # try:
    #     bootstrap = RegistrationBootstrap.find_by_identifier(filing.temp_reg)

    #     rv = AccountService.create_affiliation(
    #         account=bootstrap.account,
    #         business_registration=business.identifier,
    #         business_name=business.legal_name,
    #         corp_type_code=business.legal_type
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
    #             corp_type_code='TMP'
    #         )

    #     if rv not in (HTTPStatus.OK, HTTPStatus.CREATED) \
    #             or ('deaffiliation' in locals() and deaffiliation != HTTPStatus.OK) \
    #             or ('bootstrap_update' in locals() and bootstrap_update != HTTPStatus.OK):
    #         raise DefaultException
    # except Exception as err:  # pylint: disable=broad-except; note out any exception, but don't fail the call
    #     sentry_sdk.print(
    #         f'Queue Error: Affiliation error for filing:{filing.id}, with err:{err}',
    #         level='error'
    #     )


def _update_cooperative(incorp_filing: Dict, business: LegalEntity, filing: Filing):
    cooperative_obj = incorp_filing.get("cooperative", None)  # noqa F841; remove this comment when below is done
    # TODO remove all this
    # if cooperative_obj:
    #     # create certified copy for rules document
    #     rules_file_key = cooperative_obj.get('rulesFileKey')
    #     rules_file = MinioService.get_file(rules_file_key)
    #     registrar_stamp_data = RegistrarStampData(business.founding_date, business.identifier)

    #     replace_file_with_certified_copy(rules_file.data, rules_file_key, registrar_stamp_data)

    #     business.association_type = cooperative_obj.get('cooperativeAssociationType')
    #     document = Document()
    #     document.type = DocumentType.COOP_RULES.value
    #     document.file_key = rules_file_key
    #     document.business_id = business.id
    #     document.filing_id = filing.id
    #     business.documents.append(document)

    #     # create certified copy for memorandum document
    #     memorandum_file_key = cooperative_obj.get('memorandumFileKey')
    #     memorandum_file = MinioService.get_file(memorandum_file_key)
    #     registrar_stamp_data = RegistrarStampData(business.founding_date, business.identifier)
    #     replace_file_with_certified_copy(memorandum_file.data, memorandum_file_key, registrar_stamp_data)

    #     document = Document()
    #     document.type = DocumentType.COOP_MEMORANDUM.value
    #     document.file_key = memorandum_file_key
    #     document.business_id = business.id
    #     document.filing_id = filing.id
    #     business.documents.append(document)

    return business


def process(
    business: any,  # pylint: disable=too-many-branches,too-many-locals
    filing: Dict,
    filing_rec: Filing,
    filing_meta: FilingMeta,
):  # pylint: disable=too-many-branches
    """Process the incoming incorporation filing."""
    # Extract the filing information for incorporation
    incorp_filing = filing.get("filing", {}).get("incorporationApplication")
    filing_meta.incorporation_application = {}

    if not incorp_filing:
        raise DefaultException(f"IA legal_filing:incorporationApplication missing from {filing_rec.id}")
    if business:
        raise DefaultException(f"Business Already Exist: IA legal_filing:incorporationApplication {filing_rec.id}")

    business_info_obj = incorp_filing.get("nameRequest")

    if filing_rec.colin_event_ids:
        corp_num = filing["filing"]["business"]["identifier"]
    else:
        # Reserve the Corp Number for this entity
        corp_num = legal_entity_info.get_next_corp_num(business_info_obj["legalType"])
        if not corp_num:
            raise DefaultException(
                f"incorporationApplication {filing_rec.id} unable to get a business registration number."
            )

    # Initial insert of the business record
    business = LegalEntity()
    business = legal_entity_info.update_legal_entity_info(corp_num, business, business_info_obj, filing_rec)
    business = _update_cooperative(incorp_filing, business, filing_rec)
    business.state = BusinessCommon.State.ACTIVE

    if nr_number := business_info_obj.get("nrNumber", None):
        filing_meta.incorporation_application = {
            **filing_meta.incorporation_application,
            **{
                "nrNumber": nr_number,
                "legalName": business_info_obj.get("legalName", None),
            },
        }

    if not business:
        raise DefaultException(f"IA incorporationApplication {filing_rec.id}, Unable to create business.")

    if offices := incorp_filing["offices"]:
        update_offices(business, offices)

    if parties := incorp_filing.get("parties"):
        merge_all_parties(business, filing_rec, {"parties": parties})

    if share_structure := incorp_filing.get("shareStructure"):
        shares.update_share_structure(business, share_structure)

    if name_translations := incorp_filing.get("nameTranslations"):
        aliases.update_aliases(business, name_translations)

    if court_order := incorp_filing.get("courtOrder"):
        filings.update_filing_court_order(filing_rec, court_order)

    if not filing_rec.colin_event_ids:
        # Update the filing json with identifier and founding date.
        ia_json = copy.deepcopy(filing_rec.filing_json)
        if not ia_json["filing"].get("business"):
            ia_json["filing"]["business"] = {}
        ia_json["filing"]["business"]["identifier"] = business.identifier
        ia_json["filing"]["business"]["legalType"] = business.entity_type
        ia_json["filing"]["business"]["foundingDate"] = business.founding_date.isoformat()
        filing_rec._filing_json = ia_json  # pylint: disable=protected-access; bypass to update filing data
    return business, filing_rec, filing_meta


def post_process(business: LegalEntity, filing: Filing):
    """Post processing activities for incorporations.

    THIS SHOULD NOT ALTER THE MODEL
    """
