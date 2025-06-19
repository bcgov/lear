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
"""The Unit Tests for the Change of Officer filing."""
import copy
from datetime import datetime, timezone

import pytest
import random
from datedelta import datedelta
from business_model.models import PartyRole, Party, PartyClass, Filing
from business_model.models.types.party_class_type import PartyClassType
from registry_schemas.example_data import FILING_TEMPLATE, FILING_HEADER
from sqlalchemy import select

from business_filer.filing_meta import FilingMeta
from business_filer.filing_processors import change_of_officers
from tests.unit import create_business, factory_batch, factory_batch_processing, create_filing

CHANGE_OF_OFFICERS = {
    'relationships': [
        {
            'entity': {
                'givenName': 'Phillip Tandy',
                'familyName': 'Miller',
                'alternateName': 'Phil Miller'
            },
            'deliveryAddress': {
                'streetAddress': 'delivery_address - address line one',
                'addressCity': 'delivery_address city',
                'addressCountry': 'CA',
                'postalCode': 'H0H0H0',
                'addressRegion': 'BC'
            },
            'mailingAddress': {
                'streetAddress': 'mailing_address - address line one',
                'addressCity': 'mailing_address city',
                'addressCountry': 'CA',
                'postalCode': 'H0H0H0',
                'addressRegion': 'BC'
            },
            'roles': [
                {
                    'appointmentDate': '2018-01-01',
                    'roleType': 'CEO',
                    'roleClass': 'OFFICER'
                },
                {
                    'appointmentDate': '2018-01-01',
                    'roleType': 'Chair',
                    'roleClass': 'OFFICER'
                }
            ]
        },
        {
            'entity': {
                'givenName': 'Phillip Stacy',
                'familyName': 'Miller',
                'alternateName': 'Phil Miller'
            },
            'deliveryAddress': {
                'streetAddress': 'delivery_address - address line one',
                'addressCity': 'delivery_address city',
                'addressCountry': 'CA',
                'postalCode': 'H0H0H0',
                'addressRegion': 'BC'
            },
            'mailingAddress': {
                'streetAddress': 'mailing_address - address line one',
                'addressCity': 'mailing_address city',
                'addressCountry': 'CA',
                'postalCode': 'H0H0H0',
                'addressRegion': 'BC'
            },
            'roles': [
                {
                    'appointmentDate': '2018-01-01',
                    'roleType': 'President',
                    'roleClass': 'OFFICER'
                },
                {
                    'appointmentDate': '2018-01-01',
                    'roleType': 'CEO',
                    'roleClass': 'OFFICER'
                }
            ]
        }
    ]
}


def test_change_of_officers_process(app, session):
    """Assert that the Officers are updated."""
    # setup
    identifier = f'BC{random.randint(1000000, 9999999)}'
    business = create_business(identifier)

    effective_date = datetime(2023, 10, 10, 10, 0, 0, tzinfo=timezone.utc)

    filing = copy.deepcopy(FILING_TEMPLATE)
    filing['filing']['header']['name'] = 'changeOfOfficers'
    filing['filing']['header']['effectiveDate'] = str(effective_date)
    filing['filing']['business']['identifier'] = identifier
    filing['filing']['business']['legalType'] = 'BC'
    filing['filing']['changeOfOfficers'] = copy.deepcopy(CHANGE_OF_OFFICERS)

    filing_rec = create_filing('123', filing, business.id) # Filing(effective_date=effective_date, filing_json=filing)
    filing_meta = FilingMeta(application_date=effective_date)

    # test
    # no roles initially
    result = PartyRole.get_party_roles_by_class_type(business.id, PartyClassType.OFFICER, effective_date.date())

    assert len(result) == 0

    change_of_officers.process(business, filing_rec, filing_meta)

    session.commit()

    # should have 4 roles created
    result = PartyRole.get_party_roles_by_class_type(business.id, PartyClassType.OFFICER, effective_date.date())
    print("BUSINESS PARTY ROLES: ", business.party_roles)
    assert len(result) == 4
