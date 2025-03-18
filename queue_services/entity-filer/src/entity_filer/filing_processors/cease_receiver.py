# Copyright © 2025 Province of British Columbia
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
"""File processing rules and actions for the cease receiver."""
import datetime
from typing import Dict

from legal_api.models import Business, Filing, Party, PartyRole

from entity_filer.filing_meta import FilingMeta
from entity_filer.filing_processors.filing_components import update_address


def process(business: Business, filing: Dict, filing_rec: Filing, filing_meta: FilingMeta):
    # pylint: disable=too-many-branches;
    """Render the cease_receiver onto the business model objects."""
    cease_receiver_filing = filing.get('ceaseReceiver')
    if not cease_receiver_filing.get('parties'):
        return

    if parties := cease_receiver_filing.get('parties'):
        update_parties(business, parties, filing_rec)


def update_parties(business: Business, parties: dict, change_filing_rec: Filing):
    """Get existing parties."""
    # Cease the party role
    end_date_time = datetime.datetime.utcnow()
    parties_to_update = [party.get('officer').get('id') for party in parties if
                         party.get('officer').get('id') is not None]
    existing_party_roles = PartyRole.get_party_roles(business.id, end_date_time.date())
    for party_role in existing_party_roles:
        if party_role.party_id not in parties_to_update:
            party_role.cessation_date = end_date_time

    # Update parties
    for party_info in parties:
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
            if party.delivery_address:
                update_address(party.delivery_address, party_info.get('deliveryAddress'))
        if party_info.get('mailingAddress', None):
            if party.mailing_address:
                update_address(party.mailing_address, party_info.get('mailingAddress'))
