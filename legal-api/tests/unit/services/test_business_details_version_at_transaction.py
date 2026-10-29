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
"""Tests to assure the versioned business details snapshot queries.

Test-Suite to ensure that the as-of-transaction snapshots of VersionedBusinessDetailsService work as expected.
"""
from datetime import UTC, date, datetime

import pytest

from business_model.models import Address, Alias, Business, Party, PartyRole, Resolution
from legal_api.services.business_details_version import VersionedBusinessDetailsService
from registry_schemas.example_data import ANNUAL_REPORT
from tests.unit.models import factory_business, factory_completed_filing

IDENTIFIER = 'BC1234567'


def _add_party(business, first, last, city='Victoria', role=PartyRole.RoleTypes.DIRECTOR.value, cessation_date=None):
    """Create a versioned person party with a delivery address and one role on the business."""
    address = Address(city=city, street='1 St', postal_code='V8V8V8', country='CA', address_type=Address.DELIVERY)
    person = Party(first_name=first, last_name=last, party_type=Party.PartyTypes.PERSON.value,
                   delivery_address=address)
    person.save()
    party_role = PartyRole(role=role, appointment_date=datetime.now(UTC), cessation_date=cessation_date,
                           party_id=person.id, business_id=business.id)
    party_role.save()
    return person, party_role


def _complete(business):
    return factory_completed_filing(business, ANNUAL_REPORT)


def test_party_roles_at_transaction_returns_snapshot_shape(session):
    """Assert parties carry the top-level string id, role and no officer id."""
    business = factory_business(IDENTIFIER, entity_type='BC')
    person, _ = _add_party(business, 'Jane', 'Smith')
    filing = _complete(business)

    parties = VersionedBusinessDetailsService.get_party_roles_at_transaction(filing.transaction_id, business.id)

    assert len(parties) == 1
    assert parties[0]['id'] == str(person.id)
    assert parties[0]['role'] == 'director'
    assert parties[0]['officer']['firstName'] == 'Jane'
    assert 'id' not in parties[0]['officer']
    assert parties[0]['deliveryAddress']['addressCity'] == 'Victoria'


@pytest.mark.parametrize('role', [
    PartyRole.RoleTypes.OFFICER.value,
    PartyRole.RoleTypes.LIQUIDATOR.value,
    PartyRole.RoleTypes.RECEIVER.value,
])
def test_party_roles_at_transaction_includes_roles_the_old_revision_skips(session, role):
    """Assert officer/liquidator/receiver roles are returned although get_party_role_revision excludes them."""
    business = factory_business(IDENTIFIER, entity_type='BC')
    _add_party(business, 'Jane', 'Smith')
    skipped, _ = _add_party(business, 'Pat', 'Other', role=role)
    filing = _complete(business)

    old = VersionedBusinessDetailsService.get_party_role_revision(filing, business.id)
    new = VersionedBusinessDetailsService.get_party_roles_at_transaction(filing.transaction_id, business.id)

    assert str(skipped.id) not in [row['id'] for row in old]
    assert str(skipped.id) in [row['id'] for row in new]
    assert {row['role'] for row in new} == {'director', role}


def test_party_roles_at_transaction_excludes_ceased_roles(session):
    """Assert a role with a cessation date at that transaction is not returned."""
    business = factory_business(IDENTIFIER, entity_type='BC')
    _add_party(business, 'Jane', 'Smith')
    ceased, _ = _add_party(business, 'Bob', 'Lee', cessation_date=datetime.now(UTC))
    filing = _complete(business)

    parties = VersionedBusinessDetailsService.get_party_roles_at_transaction(filing.transaction_id, business.id)

    assert [row['officer']['lastName'] for row in parties] == ['Smith']
    assert str(ceased.id) not in [row['id'] for row in parties]


def test_party_roles_at_transaction_reflects_role_ceased_later(session):
    """Assert a role ceased after the transaction is present then and absent in the later snapshot."""
    business = factory_business(IDENTIFIER, entity_type='BC')
    _, party_role = _add_party(business, 'Jane', 'Smith')
    before = _complete(business)
    party_role.cessation_date = datetime.now(UTC)
    party_role.save()
    after = _complete(business)

    then = VersionedBusinessDetailsService.get_party_roles_at_transaction(before.transaction_id, business.id)
    now = VersionedBusinessDetailsService.get_party_roles_at_transaction(after.transaction_id, business.id)

    assert len(then) == 1
    assert now == []


def test_party_roles_at_transaction_reflects_historical_values(session):
    """Assert a party address and party added after the transaction do not appear in its snapshot."""
    business = factory_business(IDENTIFIER, entity_type='BC')
    person, _ = _add_party(business, 'Jane', 'Smith', city='Victoria')
    before = _complete(business)
    person.delivery_address.city = 'Nanaimo'
    person.delivery_address.save()
    person.last_name = 'Doe'
    person.save()
    _add_party(business, 'Late', 'Comer')
    after = _complete(business)

    then = VersionedBusinessDetailsService.get_party_roles_at_transaction(before.transaction_id, business.id)
    now = VersionedBusinessDetailsService.get_party_roles_at_transaction(after.transaction_id, business.id)

    assert len(then) == 1
    assert then[0]['officer']['lastName'] == 'Smith'
    assert then[0]['deliveryAddress']['addressCity'] == 'Victoria'
    assert sorted(row['officer']['lastName'] for row in now) == ['Comer', 'Doe']
    assert next(row for row in now if row['id'] == str(person.id))['deliveryAddress']['addressCity'] == 'Nanaimo'


def test_party_roles_at_transaction_is_scoped_to_the_business(session):
    """Assert parties of another business are not returned."""
    business = factory_business(IDENTIFIER, entity_type='BC')
    other_business = factory_business('BC7654321', entity_type='BC')
    _add_party(other_business, 'Other', 'Person')
    filing = _complete(business)

    assert VersionedBusinessDetailsService.get_party_roles_at_transaction(filing.transaction_id, business.id) == []


def test_business_revision_at_transaction_returns_historical_values_and_state(session):
    """Assert the business json carries the legalName and state as of the transaction."""
    business = factory_business(IDENTIFIER, entity_type='BC')
    original_name = business.legal_name
    before = _complete(business)
    business.legal_name = 'RENAMED INC.'
    business.state = Business.State.HISTORICAL
    business.save()
    after = _complete(business)

    then = VersionedBusinessDetailsService.get_business_revision_at_transaction(before.transaction_id, business.id)
    now = VersionedBusinessDetailsService.get_business_revision_at_transaction(after.transaction_id, business.id)

    assert then['legalName'] == original_name
    assert then['state'] == Business.State.ACTIVE
    assert now['legalName'] == 'RENAMED INC.'
    assert now['state'] == Business.State.HISTORICAL
    assert then['identifier'] == IDENTIFIER


def test_company_details_at_transaction_returns_all_sections(session):
    """Assert all six snapshot sections are returned with the data as of the transaction."""
    business = factory_business(IDENTIFIER, entity_type='BEN')
    person, _ = _add_party(business, 'Jane', 'Smith')
    alias = Alias(alias='ABC GMBH', type=Alias.AliasType.TRANSLATION.value, business_id=business.id)
    alias.save()
    resolution = Resolution(resolution_date=date(2024, 5, 1), resolution_type='SPECIAL', business_id=business.id)
    resolution.save()
    filing = _complete(business)

    details = VersionedBusinessDetailsService.get_company_details_at_transaction(filing.transaction_id, business.id)

    assert set(details) == {'business', 'parties', 'offices', 'shareClasses', 'nameTranslations', 'resolutions'}
    assert details['business']['identifier'] == IDENTIFIER
    assert [row['id'] for row in details['parties']] == [str(person.id)]
    assert details['nameTranslations'] == [{'id': str(alias.id), 'name': 'ABC GMBH', 'type': 'TRANSLATION'}]
    assert details['resolutions'] == [{'id': resolution.id, 'date': 'May 1, 2024', 'type': 'SPECIAL'}]
    assert details['shareClasses'] == []


def test_company_details_at_transaction_excludes_later_rows(session):
    """Assert aliases and resolutions added after the transaction are absent from its snapshot."""
    business = factory_business(IDENTIFIER, entity_type='BEN')
    before = _complete(business)
    Alias(alias='LATE GMBH', type=Alias.AliasType.TRANSLATION.value, business_id=business.id).save()
    Resolution(resolution_date=date(2024, 5, 1), resolution_type='SPECIAL', business_id=business.id).save()

    details = VersionedBusinessDetailsService.get_company_details_at_transaction(before.transaction_id, business.id)

    assert details['nameTranslations'] == []
    assert details['resolutions'] == []
