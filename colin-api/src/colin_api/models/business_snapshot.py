# Copyright © 2026 Province of British Columbia
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
"""Snapshot of a COLIN business, normalized to LEAR structure."""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Dict, Optional

import pycountry
from flask import current_app

from colin_api.exceptions import PartiesNotFoundException
from colin_api.models.business import Business
from colin_api.models.corp_party import Party
from colin_api.models.office import Office
from colin_api.models.shares import ShareObject
from colin_api.resources.db import DB


class BusinessSnapshot:  # pylint: disable=too-few-public-methods
    """Builds the LEAR-structured snapshot dict for a COLIN business."""

    # snapshot offices are limited to the two the amalgamation flow prepopulates
    OFFICE_TYPES = ('registeredOffice', 'recordsOffice')

    @classmethod
    def get_snapshot(cls, orig_identifier: str) -> Dict:
        """Return the business/parties/offices/shareClasses/resolutions snapshot."""
        identifier = orig_identifier
        if identifier.startswith('BC'):
            identifier = identifier[2:]

        con = DB.connection
        business = Business.find_by_identifier(identifier, con=con)
        cursor = con.cursor()

        try:
            parties = Party.get_current(cursor, identifier)
        except PartiesNotFoundException:
            # no current directors on file is bad data but not an error state here
            parties = []

        offices = Office.convert_obj_list(Office.get_current(cursor, identifier)) or {}

        # mirror the /sharestructure resource: current structure is the one with no end event
        share_structs = ShareObject.get_all(cursor, identifier) or []
        share_struct = next((x for x in share_structs if not x.end_event_id), None)
        share_classes = share_struct.to_dict()['shareClasses'] if share_struct else []

        resolutions = Business.get_resolutions(cursor, identifier)

        return {
            'business': cls._business_dict(business, orig_identifier, cursor),
            'parties': [cls._normalize_party(party) for party in parties],
            'offices': {
                office_type: cls._normalize_office(office)
                for office_type, office in offices.items() if office_type in cls.OFFICE_TYPES
            },
            'shareClasses': [cls._normalize_share_class(share_class) for share_class in share_classes],
            'resolutions': [{'date': date} for date in resolutions],
        }

    @classmethod
    def _business_dict(cls, business: Business, orig_identifier: str, cursor) -> Dict:
        """Return the business section in the shape of LEAR's slim business json."""
        return {
            'identifier': orig_identifier,
            'legalName': business.corp_name,
            'legalType': business.corp_type,
            'state': business.lear_state,
            # tri-state: None when COLIN can't compute good standing for the corp
            'goodStanding': business.good_standing,
            # find_by_identifier returns the COLIN 'True'/'False' string
            'adminFreeze': business.admin_freeze == 'True',
            'foundingDate': cls._to_iso_datetime(business.founding_date),
            'taxId': business.business_number,
            'hasFutureEffectiveFiling': cls._has_future_effective_filing(cursor, business.corp_num),
        }

    @staticmethod
    def _has_future_effective_filing(cursor, corp_num: str) -> bool:
        """Return whether any filing has an effective date still in the future."""
        current_date = datetime.now(timezone.utc).strftime('%Y-%m-%d')
        cursor.execute(
            """
            select count(*)
            from event join filing on event.event_id = filing.event_id
            where event.corp_num=:corp_num
            and filing.effective_dt > TO_DATE(:current_date, 'YYYY-mm-dd')
            """,
            corp_num=corp_num,
            current_date=current_date
        )
        return cursor.fetchone()[0] > 0

    @classmethod
    def _normalize_party(cls, party: Party) -> Dict:
        """Return a party in the structure of LEAR's /parties items."""
        raw = party.as_dict()
        return {
            'officer': {**raw['officer'], 'id': raw['id'], 'email': None},
            'deliveryAddress': cls._normalize_address(raw['deliveryAddress']),
            'mailingAddress': cls._normalize_address(raw['mailingAddress']),
            'roles': raw['roles'] or [],
        }

    @classmethod
    def _normalize_office(cls, office: Dict) -> Dict:
        """Return an office's addresses in LEAR structure."""
        return {
            'deliveryAddress': cls._normalize_address(office.get('deliveryAddress')),
            'mailingAddress': cls._normalize_address(office.get('mailingAddress')),
        }

    @classmethod
    def _normalize_address(cls, address: Optional[Dict]) -> Optional[Dict]:
        """Return an Address.as_dict in the structure of LEAR's address json."""
        if not address:
            return None
        return {
            'id': address.get('addressId'),
            'streetAddress': address.get('streetAddress'),
            'streetAddressAdditional': address.get('streetAddressAdditional'),
            'addressCity': address.get('addressCity'),
            'addressRegion': address.get('addressRegion'),
            'addressCountry': cls._country_to_alpha2(address.get('addressCountry')),
            'postalCode': address.get('postalCode'),
            'deliveryInstructions': address.get('deliveryInstructions'),
        }

    @classmethod
    def _normalize_share_class(cls, share_class: Dict) -> Dict:
        """Return a share class in the structure of LEAR's /share-classes items."""
        return {
            'id': share_class['id'],
            'name': share_class['name'],
            # COLIN never stores a priority - the class id preserves creation order
            'priority': share_class['displayOrder'],
            'hasMaximumShares': share_class['hasMaximumShares'],
            'maxNumberOfShares': cls._to_int(share_class['maxNumberOfShares']),
            'hasParValue': share_class['hasParValue'],
            'parValue': float(share_class['parValue']) if share_class['parValue'] is not None else None,
            'currency': share_class['currency'],
            'currencyAdditional': share_class['currencyAdditional'],
            'hasRightsOrRestrictions': share_class['hasRightsOrRestrictions'],
            'series': [cls._normalize_share_series(series) for series in share_class['series']],
        }

    @classmethod
    def _normalize_share_series(cls, series: Dict) -> Dict:
        """Return a share series in the structure of LEAR's series json."""
        return {
            'id': series['id'],
            'name': series['name'],
            'priority': series['displayOrder'],
            'hasMaximumShares': series['hasMaximumShares'],
            'maxNumberOfShares': cls._to_int(series['maxNumberOfShares']),
            'hasRightsOrRestrictions': series['hasRightsOrRestrictions'],
        }

    _country_cache: Dict[str, str] = {}

    @classmethod
    def _country_to_alpha2(cls, country: Optional[str]) -> Optional[str]:
        """Map COLIN's country description to the alpha-2 code LEAR stores."""
        if not country:
            return country
        if len(country) == 2:  # already a code
            return country
        if country not in cls._country_cache:
            try:
                cls._country_cache[country] = pycountry.countries.search_fuzzy(country)[0].alpha_2
            except LookupError:
                current_app.logger.error('Could not map COLIN country %s to an alpha-2 code', country)
                cls._country_cache[country] = country
        return cls._country_cache[country]

    @staticmethod
    def _to_int(value) -> Optional[int]:
        """Coerce an Oracle NUMBER to int, preserving None."""
        return int(value) if value is not None else None

    @staticmethod
    def _to_iso_datetime(value: Optional[str]) -> Optional[str]:
        """Rewrite convert_to_json_datetime's '-00:00' suffix to the ISO '+00:00' LEAR uses."""
        if value and value.endswith('-00:00'):
            return value[:-6] + '+00:00'
        return value
