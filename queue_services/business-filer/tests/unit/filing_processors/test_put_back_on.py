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
"""The Unit Tests for the Registrars Notation filing."""
import copy
import random
from datetime import datetime, timezone

from business_model.models import Business, Filing, Office, OfficeType
from registry_schemas.example_data import PUT_BACK_ON, FILING_HEADER

from business_filer.filing_meta import FilingMeta
from business_filer.filing_processors import put_back_on
from tests.unit import (
    create_business,
    create_filing,
    create_office,
    create_office_address,
    create_party,
    create_party_role,
)


def test_worker_put_back_on(app, session):
    """Assert that the put back on object is correctly populated to model objects."""
    identifier = 'BC1234567'
    business = create_business(identifier, legal_type='BC')

    party1 = create_party({
        'officer': {
            'firstName': '',
            'lastName': '',
            'middleName': '',
            'organizationName': 'Xyz some super super super super super super long business 12345678 name Inc.',
            'partyType': 'organization'
        },
        'mailingAddress': {
            'streetAddress': 'mailing_address - address line one',
            'streetAddressAdditional': '',
            'addressCity': 'mailing_address city',
            'addressCountry': 'CA',
            'postalCode': 'H0H0H0',
            'addressRegion': 'BC'
        },
        'deliveryAddress': {
            'streetAddress': 'delivery_address - address line one',
            'streetAddressAdditional': '',
            'addressCity': 'delivery_address city',
            'addressCountry': 'CA',
            'postalCode': 'H0H0H0',
            'addressRegion': 'BC'
        }
    })

    create_party_role(business, party1, ['custodian'], datetime.now(timezone.utc))
    business.save()

    office = create_office(business, 'custodialOffice')
    create_office_address(business, office, 'delivery')
    create_office_address(business, office, 'mailing')

    filing_json = copy.deepcopy(FILING_HEADER)
    filing_json['filing']['business']['identifier'] = identifier
    filing_json['filing']['putBackOn'] = copy.deepcopy(PUT_BACK_ON)

    payment_id = str(random.SystemRandom().getrandbits(0x58))
    filing = (create_filing(payment_id, filing_json, business_id=business.id))

    filing_msg = {'filing': {'id': filing.id}}

    filing_meta = FilingMeta()
    filing = create_filing('123', filing_json)

    # Test
    put_back_on.process(business, filing_json['filing'], filing, filing_meta)
    business.save()

    # Check outcome
    final_filing = Filing.find_by_id(filing.id)

    assert business.state == Business.State.ACTIVE
    assert business.state_filing_id == final_filing.id
    assert business.dissolution_date is None
    assert filing_json['filing']['putBackOn']['details'] == final_filing.order_details

    custodial_office = session.query(Business, Office). \
        filter(Business.id == Office.business_id). \
        filter(Business.id == business.id). \
        filter(Office.office_type == OfficeType.CUSTODIAL). \
        one_or_none()
    assert not custodial_office

    party_roles = business.party_roles.all()
    assert len(party_roles) == 1
    custodian = party_roles[0]
    assert custodian.role == 'custodian'
    assert custodian.cessation_date
