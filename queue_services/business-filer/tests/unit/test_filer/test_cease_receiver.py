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
"""The Unit Tests for the Cease Receiver filing."""

import copy
import random
from datetime import datetime, timezone

from business_model.models import PartyRole
from registry_schemas.example_data import CEASE_RECEIVER, FILING_TEMPLATE

from business_filer.filing_meta import FilingMeta
from business_filer.filing_processors import cease_receiver
from tests.unit import create_business, create_filing, create_party, create_party_role


def test_cease_receiver_filing_process(app, session):
    """Assert that the cease receiver object is correctly populated to model objects."""
    # Setup
    identifier = f'BC{random.randint(1000000, 9999999)}'
    business = create_business(identifier, legal_type='BC')
    role = PartyRole.RoleTypes.RECEIVER.value

    party = create_party({
        'officer': {
            'firstName': f'{role} first_name',
            'lastName': 'Doe',
            'middleName': 'P',
        },
        'mailingAddress': {
            'streetAddress': f'{role} mailing_address',
            'addressCity': 'mailing_address city',
            'addressCountry': 'CA',
            'postalCode': 'H0H0H0',
            'addressRegion': 'BC'
        },
        'deliveryAddress': {
            'streetAddress': f'{role} delivery_address',
            'addressCity': 'delivery_address city',
            'addressCountry': 'CA',
            'postalCode': 'H0H0H0',
            'addressRegion': 'BC'
        }
    })
    create_party_role(business, party, [role], datetime.now(timezone.utc))
    business.save()

    # Create filing
    filing_json = copy.deepcopy(FILING_TEMPLATE)
    filing_json['filing']['header']['name'] = 'ceaseReceiver'
    filing_json['filing']['business']['identifier'] = identifier
    filing_json['filing']['ceaseReceiver'] = copy.deepcopy(CEASE_RECEIVER)
    filing_json['filing']['ceaseReceiver']['parties'][0]['officer']['id'] = business.party_roles.all()[0].party_id

    payment_id = str(random.SystemRandom().getrandbits(0x58))
    filing = create_filing(payment_id, filing_json, business_id=business.id)

    filing_meta = FilingMeta()

    # Test
    cease_receiver.process(business, filing_json['filing'], filing, filing_meta)
    business.save()

    # Assertions
    assert len(business.party_roles.all()) == 1
    assert business.party_roles.all()[0].cessation_date is not None
