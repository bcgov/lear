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
from legal_api.models import Address, Business, Filing, Party, PartyRole

from entity_filer.filing_meta import FilingMeta
from entity_filer.filing_processors.filing_components import business_info, business_profile,\
    create_party, create_role, filings, update_address, name_request


def process(business: Business, change_filing_rec: Filing, change_filing: Dict, filing_meta: FilingMeta):
    """Render the change of registration filing onto the business model objects."""
    print(business.legal_name)
    filing_meta.change_of_registration = {}
    # Update business legalName if present
    with suppress(IndexError, KeyError, TypeError):
        name_request_json = dpath.util.get(change_filing, '/changeOfRegistration/nameRequest')
        if name_request_json.get('legalName'):
            from_legal_name = business.legal_name
            business_info.set_legal_name(business.identifier, business, name_request_json)
            print(from_legal_name)
            print(business.legal_name)
            if from_legal_name != business.legal_name:
                filing_meta.change_of_registration = {**filing_meta.change_of_registration,
                                                    **{'fromLegalName': from_legal_name,
                                                       'toLegalName': business.legal_name}}
    # Update business address if present
    with suppress(IndexError, KeyError, TypeError):
        business_address_json = dpath.util.get(change_filing, '/changeOfRegistration/businessAddress')
        for k, updated_address in business_address_json.items():
            if updated_address.get('id', None):
                address = Address.find_by_id(updated_address.get('id'))
                if address:
                    update_address(address, updated_address)

    with suppress(IndexError, KeyError, TypeError):
        party_json = dpath.util.get(change_filing, '/changeOfRegistration/parties')
        # _update_parties(business, party_json, change_filing_rec)

    # update court order, if any is present
    with suppress(IndexError, KeyError, TypeError):
        court_order_json = dpath.util.get(change_filing, '/changeOfRegistration/courtOrder')
        filings.update_filing_court_order(change_filing_rec, court_order_json)


def _update_parties(business: Business, parties: dict, change_filing_rec: Filing):
    """Create a new party or get them if they already exist."""
    for party_info in parties:
        # Create if id not present
        if not party_info.get('id'):
            _create_party_info(business, change_filing_rec, party_info)
        else:
            # Update if id is present
            _update_party(party_info)

    # Cease the party roles not present in the edit request
    end_date_time = datetime.utcnow()
    parties_to_update = [party.get('id') for party in parties if party.get('id') is not None]
    existing_party_roles = PartyRole.get_party_roles(business.id, end_date_time.date())
    for party_role in existing_party_roles:
        if party_role.party_id not in parties_to_update:
            party_role.cessation_date = end_date_time


def _update_party(party_info):
    party = Party.find_party_by_id(party_id=party_info.get('id'))
    if party:
        party.first_name = party_info['officer'].get('firstName', '').upper(),
        party.last_name = party_info['officer'].get('lastName', '').upper(),
        party.middle_initial = party_info['officer'].get('middleInitial', '').upper(),
        party.title = party_info.get('title', '').upper(),
        party.organization_name = party_info['officer'].get('organizationName', '').upper(),
        party.party_type = party_info['officer'].get('partyType')
        # add addresses to party
        if party_info.get('deliveryAddress', None):
            update_address(party.delivery_address, party_info.get('deliveryAddress'))
        if party_info.get('mailingAddress', None):
            update_address(party.mailing_address, party_info.get('mailingAddress'))


def _create_party_info(business, change_filing_rec, party_info):
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
            change_filing_rec.filing_party_roles.append(party_role)
        else:
            business.party_roles.append(party_role)


def post_process(business: Business, filing: Filing):
    """Post processing activities for change of registration.

    THIS SHOULD NOT ALTER THE MODEL
    """
    if name_request.has_new_nr_for_filing(business, filing.filing_json, 'changeOfRegistration'):
        name_request.consume_nr(business, filing, '/filing/changeOfRegistration/nrNumber')

    with suppress(IndexError, KeyError, TypeError):
        if err := business_profile.update_business_profile(
            business,
            filing.json['filing']['changeOfRegistration']['contactPoint']
        ):
            sentry_sdk.capture_message(
                f'Queue Error: Update Business for filing:{filing.id},error:{err}',
                level='error')