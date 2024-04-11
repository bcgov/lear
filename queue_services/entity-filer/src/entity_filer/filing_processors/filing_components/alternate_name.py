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
"""Manages the parties and party roles for a LegalEntity."""
from __future__ import annotations

import datetime
from typing import Dict, List, Optional, Tuple

import dpath
from business_model import AlternateName, BusinessCommon, ColinEntity, Filing, LegalEntity

from entity_filer import db
from entity_filer.exceptions import DefaultException
from entity_filer.filing_meta import FilingMeta
from entity_filer.filing_processors.filing_components import legal_entity_info
from entity_filer.filing_processors.filing_components.parties import get_or_create_party
from entity_filer.utils.legislation_datetime import LegislationDatetime


def update_partner_change(
    legal_entity: LegalEntity,
    filing_type: str,
    change_filing_rec: Filing,
    change_filing: Dict,
    filing_meta: Dict,
):
    name_request = dpath.util.get(change_filing, f"/{filing_type}/nameRequest", default=None)
    if name_request and (to_legal_name := name_request.get("legalName")):
        alternate_name = AlternateName.find_by_identifier(legal_entity.identifier)
        parties_dict = dpath.util.get(change_filing, f"/{filing_type}/parties")

        legal_entity._legal_name = get_partnership_name(parties_dict)

        legal_entity.alternate_names.remove(alternate_name)
        alternate_name.end_date = change_filing_rec.effective_date
        alternate_name.change_filing_id = change_filing_rec.id

        if start := change_filing.get("filing", {}).get(f"{filing_type}", {}).get("startDate"):
            business_start_date = LegislationDatetime.as_utc_timezone_from_legislation_date_str(start)
            legal_entity.start_date = business_start_date
        else:
            business_start_date = alternate_name.business_start_date

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
            name_type=AlternateName.NameType.DBA,
            start_date=alternate_name.start_date,
            business_start_date=business_start_date,
            state=BusinessCommon.State.ACTIVE,
            entity_type=BusinessCommon.EntityTypes.PARTNERSHIP,
            naics_key=alternate_name.naics_key,
            naics_code=alternate_name.naics_code,
            naics_description=alternate_name.naics_description,
        )
        legal_entity.alternate_names.append(new_alternate_name)

        filing_meta.update(
            {
                "fromLegalName": alternate_name.name,
                "toLegalName": to_legal_name,
            }
        )

    # Update nature of business for LegalEntity and AlternateName
    current_alternate_name = AlternateName.find_by_identifier(legal_entity.identifier)
    if (naics := change_filing.get(f"{filing_type}", {}).get("business", {}).get("naics")) and (
        naics_code := naics.get("naicsCode")
    ):
        if legal_entity.naics_code != naics_code:
            filing_meta.update(
                {
                    "fromNaicsCode": legal_entity.naics_code,
                    "toNaicsCode": naics_code,
                    "naicsDescription": naics.get("naicsDescription"),
                }
            )
            legal_entity_info.update_naics_info(legal_entity, naics)
            legal_entity_info.update_naics_info(current_alternate_name, naics)

    return legal_entity, current_alternate_name


def update_proprietor_change(
    filing_type: str,
    change_filing_rec: Filing,
    change_filing: Dict,
    filing_meta: Dict,
):
    # Update proprietor information
    if parties_dict := dpath.util.get(change_filing, f"/{filing_type}/parties", default=None):
        # Find the Proprietor
        proprietor = None
        proprietor_dict = None
        for party in parties_dict:
            for role in party.get("roles"):
                if role.get("roleType") == "Proprietor":
                    proprietor_dict = party
                    break
            if proprietor_dict:
                break

        if not proprietor_dict:
            raise DefaultException(f"No Proprietor in the SP {filing_type} for filing:{change_filing_rec.id}")

        proprietor, delivery_address, mailing_address = get_or_create_party(proprietor_dict, change_filing_rec)

        if not proprietor:
            raise DefaultException(f"No Proprietor in the SP {filing_type} for filing:{change_filing_rec.id}")

    # Update operating name
    name_request = dpath.util.get(change_filing, f"/{filing_type}/nameRequest", default=None)
    identifier = dpath.util.get(change_filing_rec.filing_json, "filing/business/identifier")
    if name_request and (to_legal_name := name_request.get("legalName")):
        alternate_name = AlternateName.find_by_identifier(identifier)
        proprietor = (
            LegalEntity.find_by_id(alternate_name.legal_entity_id)
            if alternate_name.legal_entity_id
            else ColinEntity.find_by_id(alternate_name.colin_entity_id)
        )

        if start := change_filing.get("filing", {}).get(f"{filing_type}", {}).get("startDate"):
            business_start_date = LegislationDatetime.as_utc_timezone_from_legislation_date_str(start)
        else:
            business_start_date = alternate_name.business_start_date

        if isinstance(proprietor, LegalEntity) and proprietor.entity_type == BusinessCommon.EntityTypes.PERSON:
            delivery_address_id = None
            mailing_address_id = None
        else:
            delivery_address_id = delivery_address.id if delivery_address else None
            mailing_address_id = mailing_address.id if mailing_address else None

        alternate_name.end_date = change_filing_rec.effective_date
        alternate_name.change_filing_id = change_filing_rec.id

        # alternate_name.delete()
        db.session.add(alternate_name)
        db.session.commit()
        db.session.delete(alternate_name)
        db.session.commit()

        new_alternate_name = AlternateName(
            identifier=identifier,
            name_type=AlternateName.NameType.DBA,
            change_filing_id=change_filing_rec.id,
            end_date=None,
            name=to_legal_name,
            start_date=alternate_name.start_date,
            business_start_date=business_start_date,
            delivery_address_id=delivery_address_id,
            mailing_address_id=mailing_address_id,
            bn15=alternate_name.bn15,
            email=proprietor.email,
            state=BusinessCommon.State.ACTIVE,
            entity_type=BusinessCommon.EntityTypes.SOLE_PROP,
            naics_key=alternate_name.naics_key,
            naics_code=alternate_name.naics_code,
            naics_description=alternate_name.naics_description,
        )
        proprietor.alternate_names.append(new_alternate_name)

        filing_meta.update(
            {
                "fromLegalName": alternate_name.name,
                "toLegalName": to_legal_name,
            }
        )

        # Update nature of business for AlternateName
        if (naics := change_filing.get(f"{filing_type}", {}).get("business", {}).get("naics")) and (
            naics_code := naics.get("naicsCode")
        ):
            if new_alternate_name.naics_code != naics_code:
                filing_meta.update(
                    {
                        "fromNaicsCode": new_alternate_name.naics_code,
                        "toNaicsCode": naics_code,
                        "naicsDescription": naics.get("naicsDescription"),
                    }
                )
                legal_entity_info.update_naics_info(new_alternate_name, naics)

        return proprietor, new_alternate_name

    return None, None


def get_partnership_name(parties_dict: dict):
    """Set the legal_name of the partnership."""
    parties = []
    # get all parties in an array
    for party in parties_dict:
        if officer := party.get("officer"):
            if org_name := officer.get("organizationName"):
                parties.append(org_name.upper())
                continue

            name = officer["lastName"]
            if first_name := officer.get("firstName"):
                name = f"{name} {first_name}"
            if middle_name := officer.get("middleName"):
                name = f"{name} {middle_name}"
            parties.append(name.upper())

    if len(parties) < 2:
        return parties[0]

    parties.sort()
    if parties and len(parties) > 2:
        legal_name_str = ", ".join(parties[:2])
        legal_name_str = f"{legal_name_str}, et al"
    else:
        legal_name_str = ", ".join(parties)
    return legal_name_str
