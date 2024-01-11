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
"""File processing rules and actions for historic conversion filing.

A conversion filing is for a business that was created before COLIN,
the original system to manage business corporations.

As the business exists, no new registration identifiers, names, or structures are
altered.

There are no corrections for a conversion filing.
"""
# pylint: disable=superfluous-parens; as pylance requires it
from contextlib import suppress
from typing import Dict

import dpath

# from entity_queue_common.service_utils import BusinessException
from business_model import db, AlternateName, LegalEntity, Filing
from entity_filer.utils.legislation_datetime import LegislationDatetime

from entity_filer.exceptions import BusinessException, DefaultException
from entity_filer.filing_meta import FilingMeta

from entity_filer.filing_processors.filing_components import (
    aliases,
    legal_entity_info,
    name_request,
    shares,
)
from entity_filer.filing_processors.filing_components.offices import update_offices
from entity_filer.filing_processors.filing_components.parties import merge_all_parties


def process(
    legal_entity: LegalEntity,  # pylint: disable=too-many-branches
    filing: Dict,
    filing_rec: Filing,
    filing_meta: FilingMeta,
):  # pylint: disable=too-many-branches
    """Process the incoming historic conversion filing."""
    # Extract the filing information for incorporation
    filing_meta.conversion = {}
    if not (conversion_filing := filing.get("filing", {}).get("conversion")):
        raise BusinessException(
            f"CONVL legal_filing:conversion missing from {filing_rec.id}"
        )
    # if legal_entity and legal_entity.entity_type in ['SP', 'GP']:
    if filing["filing"]["business"]["legalType"] in ["SP", "GP"]:
        if legal_entity and not legal_entity.entity_type in [
            LegalEntity.EntityTypes.PERSON,
            LegalEntity.EntityTypes.PARTNERSHIP,
        ]:
            raise DefaultException(
                f"Filing business type and entity don't match, filing{filing_rec.id}"
            )
        _process_firms_conversion(legal_entity, filing, filing_rec, filing_meta)
    else:
        legal_entity = _process_corps_conversion(
            legal_entity, conversion_filing, filing, filing_rec
        )

    return legal_entity, filing_rec


def _process_corps_conversion(legal_entity, conversion_filing, filing, filing_rec):
    if legal_entity:
        raise BusinessException(
            f"Business Already Exist: CONVL legal_filing:conversion {filing_rec.id}"
        )
    if not (corp_num := filing.get("filing", {}).get("business", {}).get("identifier")):
        raise BusinessException(
            f"conversion {filing_rec.id} missing the legal_entity identifier."
        )
    # Initial insert of the legal_entity record
    legal_entity_info_obj = conversion_filing.get("nameRequest")
    if not (
        legal_entity := legal_entity_info.update_legal_entity_info(
            corp_num, LegalEntity(), legal_entity_info_obj, filing_rec
        )
    ):
        raise BusinessException(
            f"CONVL conversion {filing_rec.id}, Unable to create legal_entity."
        )
    if offices := conversion_filing.get("offices"):
        update_offices(legal_entity, offices)
    if parties := conversion_filing.get("parties"):
        merge_all_parties(legal_entity, filing_rec, {"parties": parties})
    if share_structure := conversion_filing.get("shareStructure"):
        shares.update_share_structure(legal_entity, share_structure)
    if name_translations := conversion_filing.get("nameTranslations"):
        aliases.update_aliases(legal_entity, name_translations)
    return legal_entity


def _process_firms_conversion(
    legal_entity: LegalEntity,
    conversion_filing: Dict,
    filing_rec: Filing,
    filing_meta: FilingMeta,
):
    match legal_entity.entity_type:
        case LegalEntity.EntityTypes.PARTNERSHIP:
            _update_partner_change(
                legal_entity,
                filing_rec,
                conversion_filing,
                filing_meta
            )
        case _: # LegalEntity.EntityTypes.SOLE_PROP: # legal_entity might be a proprietor?
            _update_sp_change(
                legal_entity,
                filing_rec,
                conversion_filing,
                filing_meta
            )

    # Name change if present
    with suppress(IndexError, KeyError, TypeError):
        name_request_json = dpath.util.get(
            conversion_filing, "/filing/conversion/nameRequest"
        )
        if name_request_json.get("legalName"):
            from_legal_name = legal_entity.legal_name
            legal_entity_info.set_legal_name(
                legal_entity.identifier, legal_entity, name_request_json
            )
            if from_legal_name != legal_entity.legal_name:
                filing_meta.conversion = {
                    **filing_meta.conversion,
                    **{
                        "fromLegalName": from_legal_name,
                        "toLegalName": legal_entity.legal_name,
                    },
                }
    # Update Nature of Business
    if (
        naics := conversion_filing.get("filing", {})
        .get("conversion", {})
        .get("legal_entity", {})
        .get("naics")
    ) and naics.get("naicsDescription"):
        legal_entity_info.update_naics_info(legal_entity, naics)
        filing_meta.conversion = {
            **filing_meta.conversion,
            **{"naicsDescription": naics.get("naicsDescription")},
        }

    # Update legal_entity office if present
    with suppress(IndexError, KeyError, TypeError):
        offices_json = dpath.util.get(conversion_filing, "/filing/conversion/offices")
        update_offices(legal_entity, offices_json)

    # Update parties
    with suppress(IndexError, KeyError, TypeError):
        parties = dpath.util.get(conversion_filing, "/filing/conversion/parties")
        merge_all_parties(legal_entity, conversion_filing, {"parties": parties})

    # update legal_entity start date, if any is present
    with suppress(IndexError, KeyError, TypeError):
        legal_entity_start_date = dpath.util.get(
            conversion_filing, "/filing/conversion/startDate"
        )
        if legal_entity_start_date:
            legal_entity.start_date = (
                LegislationDatetime.as_utc_timezone_from_legislation_date_str(
                    legal_entity_start_date
                )
            )


def _update_partner_change(
        legal_entity: LegalEntity,
        change_filing_rec: Filing,
        change_filing: Dict,
        filing_meta: FilingMeta,
):
    name_request = dpath.util.get(change_filing, "/conversion/nameRequest", default=None)
    if name_request and (to_legal_name := name_request.get("legalName")):
        alternate_name = AlternateName.find_by_identifier(legal_entity.identifier)
        parties_dict = dpath.util.get(change_filing, "/conversion/parties")

        legal_entity.legal_name = get_partnership_name(parties_dict)

        legal_entity.alternate_names.remove(alternate_name)
        alternate_name.end_date = change_filing_rec.effective_date
        alternate_name.change_filing_id = change_filing_rec.id
        # alternate_name.delete()
        db.session.add(alternate_name)
        db.session.commit()
        db.session.delete(alternate_name)
        db.session.commit()


        new_alternate_name = AlternateName(
            bn15=alternate_name.bn15,
            change_filing_id=change_filing_rec.id,
            end_date=None,
            identifier=legal_entity.identifier,
            name=to_legal_name,
            name_type=AlternateName.NameType.OPERATING,
            start_date=alternate_name.start_date,
            registration_date=change_filing_rec.effective_date,
        )
        legal_entity.alternate_names.append(new_alternate_name)

        filing_meta.conversion = {
            **filing_meta.conversion,
            "fromLegalName": alternate_name.name,
            "toLegalName": to_legal_name,
        }

    # Update Nature of LegalEntity
    if (
        naics := change_filing.get("conversion", {})
        .get("business", {})
        .get("naics")
    ) and (naics_code := naics.get("naicsCode")):
        if legal_entity.naics_code != naics_code:
            filing_meta.conversion = {
                **filing_meta.conversion,
                **{
                    "fromNaicsCode": legal_entity.naics_code,
                    "toNaicsCode": naics_code,
                    "naicsDescription": naics.get("naicsDescription"),
                },
            }
            legal_entity_info.update_naics_info(legal_entity, naics)


def _update_sp_change(
        legal_entity: LegalEntity,
        change_filing_rec: Filing,
        change_filing: Dict,
        filing_meta: FilingMeta,
):
    name_request = dpath.util.get(change_filing, "/conversion/nameRequest", default=None)
    identifier = dpath.util.get(change_filing_rec.filing_json, "filing/business/identifier")
    if name_request and (to_legal_name := name_request.get("legalName")):
        alternate_name = AlternateName.find_by_identifier(identifier)
        parties_dict = dpath.util.get(change_filing, "/conversion/parties")

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
            raise DefaultException(
                f"No Proprietor in the SP conversion for filing:{change_filing_rec.id}"
            )

        proprietor, delivery_address, mailing_address = get_or_create_party(
            proprietor_dict, change_filing_rec
        )
        if not proprietor:
            raise DefaultException(
                f"No Proprietor in the SP conversion for filing:{change_filing_rec.id}"
            )

        alternate_name.end_date = change_filing_rec.effective_date
        alternate_name.change_filing_id = change_filing_rec.id
        # alternate_name.delete()
        db.session.add(alternate_name)
        db.session.commit()
        db.session.delete(alternate_name)
        db.session.commit()

        new_alternate_name = AlternateName(
            identifier=identifier,
            name_type=AlternateName.NameType.OPERATING,
            change_filing_id=change_filing_rec.id,
            end_date=None,
            name=to_legal_name,
            start_date=alternate_name.start_date,
            registration_date=change_filing_rec.effective_date,
        )
        proprietor.alternate_names.append(new_alternate_name)

        filing_meta.conversion = {
            **filing_meta.conversion,
            "fromLegalName": alternate_name.name,
            "toLegalName": to_legal_name,
        }


def post_process(legal_entity: LegalEntity, filing: Filing):
    """Post processing activities for conversion ledger.

    THIS SHOULD NOT ALTER THE MODEL
    """
    name_request.consume_nr(legal_entity, filing, "conversion")
