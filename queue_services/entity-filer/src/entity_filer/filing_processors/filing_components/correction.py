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
"""File processing rules and actions for the correction filing."""
import copy
import datetime
from contextlib import suppress
from typing import Dict

import dpath
from legal_api.models import Address, Business, Filing, Party, PartyRole
from legal_api.utils.legislation_datetime import LegislationDatetime

from entity_filer.filing_meta import FilingMeta
from entity_filer.filing_processors.filing_components import (
    aliases,
    business_info,
    create_party,
    create_role,
    filings,
    resolutions,
    rules_and_memorandum,
    shares,
    update_address,
)


CEASE_ROLE_MAPPING = {
    **dict.fromkeys(Business.CORPS, PartyRole.RoleTypes.DIRECTOR.value),
    Business.LegalTypes.COOP.value: PartyRole.RoleTypes.DIRECTOR.value,
    Business.LegalTypes.PARTNERSHIP.value: PartyRole.RoleTypes.PARTNER.value,
    Business.LegalTypes.SOLE_PROP.value: PartyRole.RoleTypes.PROPRIETOR.value,
}


def correct_business_data(business: Business,  # pylint: disable=too-many-locals, too-many-statements
                          correction_filing_rec: Filing,
                          correction_filing: Dict,
                          filing_meta: FilingMeta):
    """Render the correction filing onto the business model objects."""
    # Update business legalName if present
    with suppress(IndexError, KeyError, TypeError):
        name_request_json = dpath.util.get(correction_filing, '/correction/nameRequest')
        from_legal_name = business.legal_name
        business_info.set_legal_name(business.identifier, business, name_request_json)
        if from_legal_name != business.legal_name:
            filing_meta.correction = {**filing_meta.correction,
                                      **{'fromLegalName': from_legal_name,
                                         'toLegalName': business.legal_name}}

    # Update cooperativeAssociationType if present
    with suppress(IndexError, KeyError, TypeError):
        coop_association_type = dpath.util.get(correction_filing, '/correction/cooperativeAssociationType')
        from_association_type = business.association_type
        if coop_association_type:
            business_info.set_association_type(business, coop_association_type)
            filing_meta.correction = {**filing_meta.correction,
                                      **{'fromCooperativeAssociationType': from_association_type,
                                         'toCooperativeAssociationType': business.association_type}}

    # Update Nature of Business
    if naics := correction_filing.get('correction', {}).get('business', {}).get('naics'):
        to_naics_code = naics.get('naicsCode')
        to_naics_description = naics.get('naicsDescription')
        if business.naics_description != to_naics_description:
            filing_meta.correction = {
                **filing_meta.correction,
                **{'fromNaicsCode': business.naics_code,
                   'toNaicsCode': to_naics_code,
                   'naicsDescription': to_naics_description}}
            business_info.update_naics_info(business, naics)

    # update name translations, if any
    with suppress(IndexError, KeyError, TypeError):
        alias_json = dpath.util.get(correction_filing, '/correction/nameTranslations')
        aliases.update_aliases(business, alias_json)

    # Update offices if present
    with suppress(IndexError, KeyError, TypeError):
        offices_structure = dpath.util.get(correction_filing, '/correction/offices')
        _update_addresses(offices_structure)

    # Update parties
    with suppress(IndexError, KeyError, TypeError):
        party_json = dpath.util.get(correction_filing, '/correction/parties')
        update_parties(business, party_json, correction_filing_rec)

    # update court order, if any is present
    with suppress(IndexError, KeyError, TypeError):
        court_order_json = dpath.util.get(correction_filing, '/correction/courtOrder')
        filings.update_filing_court_order(correction_filing_rec, court_order_json)

    # update business start date, if any is present
    with suppress(IndexError, KeyError, TypeError):
        business_start_date = dpath.util.get(correction_filing, '/correction/startDate')
        if business_start_date:
            business.start_date = LegislationDatetime.as_utc_timezone_from_legislation_date_str(business_start_date)

    # update share structure and resolutions, if any
    with suppress(IndexError, KeyError, TypeError):
        share_structure = dpath.util.get(correction_filing, '/correction/shareStructure')
        shares.update_share_structure_correction(business, share_structure)

    # update resolution, if any
    with suppress(IndexError, KeyError, TypeError):
        resolution = dpath.util.get(correction_filing, '/correction/resolution')
        resolutions.update_resolution(business, resolution)
        if resolution:
            filing_meta.correction = {**filing_meta.correction, **{'hasResolution': True}}

    # update signatory, if any
    with suppress(IndexError, KeyError, TypeError):
        signatory = dpath.util.get(correction_filing, '/correction/signatory')
        resolutions.update_signatory(business, signatory)

    # update business signing date, if any is present
    with suppress(IndexError, KeyError, TypeError):
        signing_date = dpath.util.get(correction_filing, '/correction/signingDate')
        resolutions.update_signing_date(business, signing_date)

    # update business resolution date, if any is present
    with suppress(IndexError, KeyError, TypeError):
        resolution_date = dpath.util.get(correction_filing, '/correction/resolutionDate')
        resolutions.update_resolution_date(business, resolution_date)

    # update rules, if any
    with suppress(IndexError, KeyError, TypeError):
        rules_file_key = dpath.util.get(correction_filing, '/correction/rulesFileKey')
        rules_file_name = dpath.util.get(correction_filing, '/correction/rulesFileName')
        if rules_file_key:
            rules_and_memorandum.update_rules(business, correction_filing_rec, rules_file_key, rules_file_name)
            filing_meta.correction = {**filing_meta.correction,
                                      **{'uploadNewRules': True}}

    # update memorandum, if any
    with suppress(IndexError, KeyError, TypeError):
        memorandum_file_key = dpath.util.get(correction_filing, '/correction/memorandumFileKey')
        memorandum_file_name = dpath.util.get(correction_filing, '/correction/memorandumFileName')
        if memorandum_file_key:
            rules_and_memorandum.update_memorandum(business, correction_filing_rec,
                                                   memorandum_file_key, memorandum_file_name)
            filing_meta.correction = {**filing_meta.correction,
                                      **{'uploadNewMemorandum': True}}

    with suppress(IndexError, KeyError, TypeError):
        if dpath.util.get(correction_filing, '/correction/memorandumInResolution'):
            filing_meta.correction = {**filing_meta.correction,
                                      **{'memorandumInResolution': True}}

    with suppress(IndexError, KeyError, TypeError):
        if dpath.util.get(correction_filing, '/correction/rulesInResolution'):
            filing_meta.correction = {**filing_meta.correction,
                                      **{'rulesInResolution': True}}


def update_parties(business: Business, parties: list, correction_filing_rec: Filing):
    """Create a new party or get them if they already exist."""
    if correction_filing_rec.colin_event_ids:
        # This may not be covering all the cases, introducing this to sync back the BEN to BC business as of today.
        directors = PartyRole.get_parties_by_role(business.id, PartyRole.RoleTypes.DIRECTOR.value)
        for party_info in parties:
            for director in directors:
                existing_director_name = \
                    director.party.first_name + director.party.middle_initial + director.party.last_name
                current_new_director_name = \
                    party_info['officer'].get('firstName') + party_info['officer'].get('middleInitial', '') + \
                    party_info['officer'].get('lastName')
                if existing_director_name.upper() == current_new_director_name.upper():
                    party_info['officer']['id'] = director.party.id
                    break

        filing_json = copy.deepcopy(correction_filing_rec.filing_json)
        filing_json['filing']['correction']['parties'] = parties
        correction_filing_rec._filing_json = filing_json  # pylint: disable=protected-access; bypass to update

    # Cease the party roles not present in the edit request
    if parties is None:
        return
    end_date_time = datetime.datetime.utcnow()
    parties_to_update = [party.get('officer').get('id') for party in parties if
                         party.get('officer').get('id') is not None]
    existing_party_roles = PartyRole.get_party_roles(business.id, end_date_time.date())
    for party_role in existing_party_roles:
        # Safety check, skip roles that should not be ceased
        if (expected_role := CEASE_ROLE_MAPPING.get(business.legal_type)) and \
                party_role.role != expected_role:
            continue
        if party_role.party_id not in parties_to_update:
            party_role.cessation_date = end_date_time

    # Create and Update
    for party_info in parties:
        # Create if id not present
        # If id is present and is a GUID then this is an id specific to the UI which is not relevant to the backend.
        # The backend will have an id of type int
        if not party_info.get('officer').get('id') or \
                (party_info.get('officer').get('id') and not isinstance(party_info.get('officer').get('id'), int)):
            _create_party_info(business, correction_filing_rec, party_info)
        else:
            # Update if id is present
            _update_party(party_info)


def _update_party(party_info):
    party = Party.find_by_id(party_id=party_info.get('officer').get('id'))
    if party:
        party.first_name = party_info['officer'].get('firstName', '').upper()
        party.last_name = party_info['officer'].get('lastName', '').upper()
        party.middle_initial = party_info['officer'].get('middleName', '').upper()
        party.title = party_info.get('title', '').upper()
        party.organization_name = party_info['officer'].get('organizationName', '').upper()
        party.party_type = party_info['officer'].get('partyType')
        party.email = party_info['officer'].get('email', '').lower()
        party.identifier = party_info['officer'].get('identifier', '').upper()
        # add addresses to party
        if party_info.get('deliveryAddress', None):
            if not party.delivery_address:
                party.delivery_address = Address()
            update_address(party.delivery_address, party_info.get('deliveryAddress'))
        if party_info.get('mailingAddress', None):
            if not party.mailing_address:
                party.mailing_address = Address()
            update_address(party.mailing_address, party_info.get('mailingAddress'))


def _create_party_info(business, correction_filing_rec, party_info):
    party = create_party(business_id=business.id, party_info=party_info, create=False)
    for role_type in party_info.get('roles'):
        role_str = role_type.get('roleType', '').lower()
        role = {
            'roleType': role_str,
            'appointmentDate': role_type.get('appointmentDate', None),
            'cessationDate': role_type.get('cessationDate', None)
        }
        party_role = create_role(party=party, role_info=role)
        if party_role.role in [PartyRole.RoleTypes.COMPLETING_PARTY.value]:
            correction_filing_rec.filing_party_roles.append(party_role)
        else:
            business.party_roles.append(party_role)


def _update_addresses(offices_structure):
    """Update addresses when offices exists."""
    for addresses in offices_structure.values():
        for updated_address in addresses.values():
            if updated_address.get('id', None):
                address = Address.find_by_id(updated_address.get('id'))
                if address:
                    update_address(address, updated_address)
