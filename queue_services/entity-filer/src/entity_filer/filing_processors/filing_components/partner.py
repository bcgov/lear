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
import dpath
from typing import Dict, List, Optional, Tuple

from business_model import db
from business_model import AlternateName
from business_model import Filing
from business_model import LegalEntity

from entity_filer import db
from entity_filer.exceptions import DefaultException
from entity_filer.filing_meta import FilingMeta
from entity_filer.filing_processors.filing_components import legal_entity_info
from entity_filer.filing_processors.filing_components.parties import get_or_create_party
from entity_filer.utils.legislation_datetime import LegislationDatetime


def update_partner_change(
        legal_entity: LegalEntity,
        filint_type: str,
        change_filing_rec: Filing,
        change_filing: Dict,
        filing_meta: Dict,
):
    name_request = dpath.util.get(change_filing, f"/{filint_type}/nameRequest", default=None)
    if name_request and (to_legal_name := name_request.get("legalName")):
        alternate_name = AlternateName.find_by_identifier(legal_entity.identifier)
        parties_dict = dpath.util.get(change_filing, f"/{filint_type}/parties")

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
            start_date=change_filing.get("startDate"),
            registration_date=change_filing_rec.effective_date,
        )
        legal_entity.alternate_names.append(new_alternate_name)

        filing_meta = {
            **filing_meta,
            "fromLegalName": alternate_name.name,
            "toLegalName": to_legal_name,
        }

    # Update Nature of LegalEntity
    if (
        naics := change_filing.get(f"{filint_type}", {})
        .get("business", {})
        .get("naics")
    ) and (naics_code := naics.get("naicsCode")):
        if legal_entity.naics_code != naics_code:
            filing_meta = {
                **filing_meta,
                **{
                    "fromNaicsCode": legal_entity.naics_code,
                    "toNaicsCode": naics_code,
                    "naicsDescription": naics.get("naicsDescription"),
                },
            }
            legal_entity_info.update_naics_info(legal_entity, naics)


def update_proprietor_change(
        filint_type: str,
        change_filing_rec: Filing,
        change_filing: Dict,
        filing_meta: Dict,
):
    name_request = dpath.util.get(change_filing, f"/{filint_type}/nameRequest", default=None)
    identifier = dpath.util.get(change_filing_rec.filing_json, "filing/business/identifier")
    if name_request and (to_legal_name := name_request.get("legalName")):
        alternate_name = AlternateName.find_by_identifier(identifier)
        parties_dict = dpath.util.get(change_filing, f"/{filint_type}/parties")

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
                f"No Proprietor in the SP {filint_type} for filing:{change_filing_rec.id}"
            )

        proprietor, delivery_address, mailing_address = get_or_create_party(
            proprietor_dict, change_filing_rec
        )
        if not proprietor:
            raise DefaultException(
                f"No Proprietor in the SP {filint_type} for filing:{change_filing_rec.id}"
            )
        
        if start := change_filing.get("filing", {}).get(f"{filint_type}", {}).get("startDate"):
            start_date = LegislationDatetime.as_utc_timezone_from_legislation_date_str(
                start
            )
        elif change_filing.effective_date:
            start_date = change_filing.effective_date.isoformat()
        else:
            start_date = LegislationDatetime.now()

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
            start_date=start_date,
            registration_date=change_filing_rec.effective_date,
        )
        proprietor.alternate_names.append(new_alternate_name)

        filing_meta = {
            **filing_meta,
            "fromLegalName": alternate_name.name,
            "toLegalName": to_legal_name,
        }


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
