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
"""File processing rules and actions for the change of registration filing."""
import datetime
from contextlib import suppress
from typing import Dict

import dpath
from business_model import db, Address, AlternateName, LegalEntity, Filing
from entity_filer.exceptions.default_exception import DefaultException

from entity_filer.filing_meta import FilingMeta
from entity_filer.filing_processors.filing_components import (
    filings,
    legal_entity_info,
    name_request,
    update_address,
)
from entity_filer.filing_processors.filing_components.parties import get_or_create_party, merge_all_parties
from entity_filer.filing_processors.registration import get_partnership_name
from entity_filer.filing_processors.filing_components.partner import update_partner_change, update_proprietor_change


def  process(
    legal_entity: LegalEntity,
    change_filing_rec: Filing,
    change_filing: Dict,
    filing_meta: FilingMeta,
):
    """Render the change of registration filing onto the business model objects."""
    filing_meta.change_of_registration = {}
    match legal_entity.entity_type:
        case LegalEntity.EntityTypes.PARTNERSHIP:
            update_partner_change(
                legal_entity=legal_entity,
                filint_type="changeOfRegistration",
                change_filing_rec=change_filing_rec,
                change_filing=change_filing,
                filing_meta=filing_meta.change_of_registration
            )
        case _: # LegalEntity.EntityTypes.SOLE_PROP: # legal_entity might be a proprietor?
            update_proprietor_change(
                legal_entity=legal_entity,
                filint_type="changeOfRegistration",
                change_filing_rec=change_filing_rec,
                change_filing=change_filing,
                filing_meta=filing_meta.change_of_registration
            )
        
    # Update business office if present
    with suppress(IndexError, KeyError, TypeError):
        business_office_json = dpath.util.get(
            change_filing, "/changeOfRegistration/offices/businessOffice"
        )
        for updated_address in business_office_json.values():
            if updated_address.get("id", None):
                address = Address.find_by_id(updated_address.get("id"))
                if address:
                    update_address(address, updated_address)

    # Update parties
    with suppress(IndexError, KeyError, TypeError):
        parties = dpath.util.get(change_filing, "/changeOfRegistration/parties")
        merge_all_parties(legal_entity, change_filing_rec, {"parties": parties})

    # update court order, if any is present
    with suppress(IndexError, KeyError, TypeError):
        court_order_json = dpath.util.get(
            change_filing, "/changeOfRegistration/courtOrder"
        )
        filings.update_filing_court_order(change_filing_rec, court_order_json)


def post_process(business: LegalEntity, filing: Filing):
    """Post processing activities for change of registration.

    THIS SHOULD NOT ALTER THE MODEL
    """
    name_request.consume_nr(business, filing, "changeOfRegistration")

# def _update_partner_change(
#         legal_entity: LegalEntity,
#         change_filing_rec: Filing,
#         change_filing: Dict,
#         filing_meta: FilingMeta,
# ):
#     name_request = dpath.util.get(change_filing, "/changeOfRegistration/nameRequest", default=None)
#     if name_request and (to_legal_name := name_request.get("legalName")):
#         alternate_name = AlternateName.find_by_identifier(legal_entity.identifier)
#         parties_dict = dpath.util.get(change_filing, "/changeOfRegistration/parties")

#         legal_entity.legal_name = get_partnership_name(parties_dict)

#         legal_entity.alternate_names.remove(alternate_name)
#         alternate_name.end_date = change_filing_rec.effective_date
#         alternate_name.change_filing_id = change_filing_rec.id
#         # alternate_name.delete()
#         db.session.add(alternate_name)
#         db.session.commit()
#         db.session.delete(alternate_name)
#         db.session.commit()


#         new_alternate_name = AlternateName(
#             bn15=alternate_name.bn15,
#             change_filing_id=change_filing_rec.id,
#             end_date=None,
#             identifier=legal_entity.identifier,
#             name=to_legal_name,
#             name_type=AlternateName.NameType.OPERATING,
#             start_date=alternate_name.start_date,
#             registration_date=change_filing_rec.effective_date,
#         )
#         legal_entity.alternate_names.append(new_alternate_name)

#         filing_meta.change_of_registration = {
#             **filing_meta.change_of_registration,
#             "fromLegalName": alternate_name.name,
#             "toLegalName": to_legal_name,
#         }

#     # Update Nature of LegalEntity
#     if (
#         naics := change_filing.get("changeOfRegistration", {})
#         .get("business", {})
#         .get("naics")
#     ) and (naics_code := naics.get("naicsCode")):
#         if legal_entity.naics_code != naics_code:
#             filing_meta.change_of_registration = {
#                 **filing_meta.change_of_registration,
#                 **{
#                     "fromNaicsCode": legal_entity.naics_code,
#                     "toNaicsCode": naics_code,
#                     "naicsDescription": naics.get("naicsDescription"),
#                 },
#             }
#             legal_entity_info.update_naics_info(legal_entity, naics)


# def _update_sp_change(
#         legal_entity: LegalEntity,
#         change_filing_rec: Filing,
#         change_filing: Dict,
#         filing_meta: FilingMeta,
# ):
#     name_request = dpath.util.get(change_filing, "/changeOfRegistration/nameRequest", default=None)
#     identifier = dpath.util.get(change_filing_rec.filing_json, "filing/business/identifier")
#     if name_request and (to_legal_name := name_request.get("legalName")):
#         alternate_name = AlternateName.find_by_identifier(identifier)
#         parties_dict = dpath.util.get(change_filing, "/changeOfRegistration/parties")

#         # Find the Proprietor
#         proprietor = None
#         for party in parties_dict:
#             for role in party.get("roles"):
#                 if role.get("roleType") == "Proprietor":
#                     proprietor_dict = party
#                     break
#             if proprietor_dict:
#                 break

#         if not proprietor_dict:
#             raise DefaultException(
#                 f"No Proprietor in the SP registration for filing:{change_filing_rec.id}"
#             )

#         proprietor, delivery_address, mailing_address = get_or_create_party(
#             proprietor_dict, change_filing_rec
#         )
#         if not proprietor:
#             raise DefaultException(
#                 f"No Proprietor in the SP registration for filing:{change_filing_rec.id}"
#             )

#         alternate_name.end_date = change_filing_rec.effective_date
#         alternate_name.change_filing_id = change_filing_rec.id
#         # alternate_name.delete()
#         db.session.add(alternate_name)
#         db.session.commit()
#         db.session.delete(alternate_name)
#         db.session.commit()

#         new_alternate_name = AlternateName(
#             identifier=identifier,
#             name_type=AlternateName.NameType.OPERATING,
#             change_filing_id=change_filing_rec.id,
#             end_date=None,
#             name=to_legal_name,
#             start_date=alternate_name.start_date,
#             registration_date=change_filing_rec.effective_date,
#         )
#         proprietor.alternate_names.append(new_alternate_name)

#         filing_meta.change_of_registration = {
#             **filing_meta.change_of_registration,
#             "fromLegalName": alternate_name.name,
#             "toLegalName": to_legal_name,
#         }
