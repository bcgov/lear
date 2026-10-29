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
"""Tests to assure the draft filing changes end-point.

Test-Suite to ensure that GET /businesses/{identifier}/filings/{filing_id}/changes is working as expected.
"""
import re
from datetime import UTC, datetime, timedelta
from http import HTTPStatus

import pytest

from business_model.models import Address, Business, Party, PartyRole
from legal_api.services.authz import BASIC_USER, STAFF_ROLE
from registry_schemas.example_data import ANNUAL_REPORT
from tests.unit.models import factory_business, factory_completed_filing, factory_filing
from tests.unit.services.utils import create_header

IDENTIFIER = 'BC1234567'


def _changes_url(filing_id, identifier=IDENTIFIER):
    return f'/api/v2/businesses/{identifier}/filings/{filing_id}/changes'


def _address(city):
    """Return the draft address that matches what _add_director writes."""
    return {'streetAddress': '1 St', 'addressCity': city, 'addressCountry': 'CA', 'postalCode': 'V8V8V8'}


def _add_director(business, first='Jane', last='Smith', city='Victoria'):
    """Create a versioned director party with a delivery address."""
    address = Address(city=city, street='1 St', postal_code='V8V8V8', country='CA', address_type=Address.DELIVERY)
    person = Party(first_name=first, last_name=last, party_type=Party.PartyTypes.PERSON.value,
                   delivery_address=address)
    person.save()
    PartyRole(role=PartyRole.RoleTypes.DIRECTOR.value, appointment_date=datetime.now(UTC),
              party_id=person.id, business_id=business.id).save()
    return person


def _draft_director(party_id, first, last, city, actions=None):
    row = {'officer': {'id': party_id, 'firstName': first, 'lastName': last},
           'roles': [{'roleType': 'Director'}],
           'deliveryAddress': _address(city),
           'mailingAddress': _address(city)}
    if actions:
        row['actions'] = actions
    return row


def _draft_cod(business, directors, base_transaction_id, filing_date=None):
    """Create a changeOfDirectors draft stamped with the given base transaction."""
    filing_json = {'filing': {'header': {'name': 'changeOfDirectors', 'date': '2024-01-01', 'certifiedBy': 'tester'},
                              'business': {'identifier': business.identifier, 'legalType': 'BC'},
                              'changeOfDirectors': {'directors': directors}}}
    kwargs = {'filing_date': filing_date} if filing_date else {}
    filing = factory_filing(business, filing_json, **kwargs)
    filing.base_transaction_id = base_transaction_id
    filing.save()
    return filing


def _get_changes(client, jwt, filing, identifier=IDENTIFIER):
    return client.get(_changes_url(filing.id, identifier), headers=create_header(jwt, [STAFF_ROLE], identifier))


def test_changes_business_not_found(session, client, jwt):
    """Assert that 404 is returned when the business does not exist."""
    rv = client.get(_changes_url(1, 'BC9999999'), headers=create_header(jwt, [STAFF_ROLE], 'BC9999999'))

    assert rv.status_code == HTTPStatus.NOT_FOUND


def test_changes_filing_not_found(session, client, jwt):
    """Assert that 404 is returned when the filing does not exist on the business."""
    factory_business(IDENTIFIER, entity_type='BC')

    rv = client.get(_changes_url(99999999), headers=create_header(jwt, [STAFF_ROLE], IDENTIFIER))

    assert rv.status_code == HTTPStatus.NOT_FOUND


def test_changes_non_draft_filing_is_bad_request(session, client, jwt):
    """Assert that 400 is returned when the filing is not a draft."""
    business = factory_business(IDENTIFIER, entity_type='BC')
    completed = factory_completed_filing(business, ANNUAL_REPORT)

    rv = _get_changes(client, jwt, completed)

    assert rv.status_code == HTTPStatus.BAD_REQUEST
    assert 'only available for draft filings' in rv.json['message']


def test_changes_unauthorized_without_view_access(session, client, jwt, requests_mock):
    """Assert that 401 is returned when the user has no view access to the business."""
    business = factory_business(IDENTIFIER, entity_type='BC')
    draft = _draft_cod(business, [], None)
    requests_mock.get(re.compile(r'.*/entities/.*/authorizations'), status_code=HTTPStatus.FORBIDDEN, json={})

    rv = client.get(_changes_url(draft.id), headers=create_header(jwt, [BASIC_USER], 'WRONGUSER'))

    assert rv.status_code == HTTPStatus.UNAUTHORIZED


def test_changes_up_to_date_when_no_completed_filings(session, client, jwt):
    """Assert that the report is upToDate with empty lists when the watermark is None."""
    business = factory_business(IDENTIFIER, entity_type='BC')
    draft = _draft_cod(business, [], None)

    rv = _get_changes(client, jwt, draft)

    assert rv.status_code == HTTPStatus.OK
    assert rv.json['upToDate'] is True
    assert rv.json['currentTransactionId'] is None
    for key in ('interveningFilings', 'changedSections', 'draftSections', 'conflicts', 'alreadyApplied'):
        assert rv.json[key] == []


def test_changes_up_to_date_when_base_equals_watermark(session, client, jwt):
    """Assert that a draft based on the watermark is upToDate with its sections but no conflicts."""
    business = factory_business(IDENTIFIER, entity_type='BC')
    person = _add_director(business)
    completed = factory_completed_filing(business, ANNUAL_REPORT)
    draft = _draft_cod(business, [_draft_director(person.id, 'Jane', 'Smith', 'Nanaimo', actions=['EDITED'])],
                       completed.transaction_id)

    rv = _get_changes(client, jwt, draft)

    assert rv.status_code == HTTPStatus.OK
    assert rv.json['upToDate'] is True
    assert rv.json['baseTransactionId'] == rv.json['currentTransactionId'] == completed.transaction_id
    assert rv.json['draftSections'] == ['parties']
    assert rv.json['conflicts'] == []
    assert rv.json['interveningFilings'] == []


def test_changes_reports_intervening_filings_and_conflict(session, client, jwt):
    """Assert that staff changes after the base show as intervening filings, a changed section and a conflict."""
    business = factory_business(IDENTIFIER, entity_type='BC')
    person = _add_director(business)
    base_filing = factory_completed_filing(business, ANNUAL_REPORT)
    draft = _draft_cod(business, [_draft_director(person.id, 'Jane', 'Smith', 'Nanaimo', actions=['EDITED'])],
                       base_filing.transaction_id)
    person.delivery_address.city = 'Vancouver'
    person.delivery_address.save()
    staff_filing = factory_completed_filing(business, ANNUAL_REPORT)
    staff_filing.submitter_roles = 'staff'
    staff_filing.save()

    rv = _get_changes(client, jwt, draft)

    assert rv.status_code == HTTPStatus.OK
    report = rv.json
    assert report['upToDate'] is False
    assert report['baseTransactionId'] == base_filing.transaction_id
    assert report['currentTransactionId'] == staff_filing.transaction_id
    assert report['draftSections'] == ['parties']
    assert report['changedSections'] == ['parties']
    assert len(report['interveningFilings']) == 1
    intervening = report['interveningFilings'][0]
    assert intervening['filingId'] == staff_filing.id
    assert intervening['name'] == 'annualReport'
    assert intervening['displayName']
    assert intervening['filedByStaff'] is True
    assert report['alreadyApplied'] == []
    assert len(report['conflicts']) == 1
    conflict = report['conflicts'][0]
    assert conflict['section'] == 'parties'
    assert conflict['entityKey'] == 'SMITH, JANE'
    assert conflict['rowId'] == person.id
    assert '/deliveryAddress/addressCity' in conflict['paths']
    assert conflict['baseValue']['deliveryAddress']['addressCity'] == 'Victoria'
    assert conflict['currentValue']['deliveryAddress']['addressCity'] == 'Vancouver'
    assert conflict['draftValue']['deliveryAddress']['addressCity'] == 'Nanaimo'


def test_changes_accumulates_multiple_intervening_filings(session, client, jwt):
    """Assert the report diffs cumulatively across every filing completed after the base."""
    business = factory_business(IDENTIFIER, entity_type='BC')
    person = _add_director(business)
    base_filing = factory_completed_filing(business, ANNUAL_REPORT)
    draft = _draft_cod(business, [_draft_director(person.id, 'Jane', 'Smith', 'Nanaimo', actions=['EDITED'])],
                       base_filing.transaction_id)

    person.delivery_address.city = 'Vancouver'
    person.delivery_address.save()
    first_filing = factory_completed_filing(business, ANNUAL_REPORT)
    first_filing.submitter_roles = 'staff'
    first_filing.save()

    person.delivery_address.city = 'Surrey'
    person.delivery_address.save()
    _add_director(business, first='Bob', last='Lee', city='Burnaby')
    second_filing = factory_completed_filing(business, ANNUAL_REPORT)

    rv = _get_changes(client, jwt, draft)

    assert rv.status_code == HTTPStatus.OK
    report = rv.json
    assert report['upToDate'] is False
    assert report['currentTransactionId'] == second_filing.transaction_id
    # every completed filing after the base is listed, oldest first, with its own provenance
    assert [f['filingId'] for f in report['interveningFilings']] == [first_filing.id, second_filing.id]
    assert [f['filedByStaff'] for f in report['interveningFilings']] == [True, False]
    assert report['changedSections'] == ['parties']
    # the conflict is against the net current value, not any intermediate one
    assert len(report['conflicts']) == 1
    conflict = report['conflicts'][0]
    assert conflict['entityKey'] == 'SMITH, JANE'
    assert conflict['currentValue']['deliveryAddress']['addressCity'] == 'Surrey'
    # the added director changed under the draft but was not draft-touched: no conflict for it
    assert report['alreadyApplied'] == []


def test_changes_reports_already_applied_when_draft_matches_current(session, client, jwt):
    """Assert that a draft edit equal to the current value is reported as alreadyApplied, not a conflict."""
    business = factory_business(IDENTIFIER, entity_type='BC')
    person = _add_director(business)
    base_filing = factory_completed_filing(business, ANNUAL_REPORT)
    draft = _draft_cod(business, [_draft_director(person.id, 'Jane', 'Smith', 'Vancouver', actions=['EDITED'])],
                       base_filing.transaction_id)
    person.delivery_address.city = 'Vancouver'
    person.delivery_address.save()
    factory_completed_filing(business, ANNUAL_REPORT)

    rv = _get_changes(client, jwt, draft)

    assert rv.status_code == HTTPStatus.OK
    assert rv.json['conflicts'] == []
    assert rv.json['alreadyApplied'] == [{'section': 'parties', 'entityKey': 'SMITH, JANE'}]
    assert rv.json['changedSections'] == ['parties']


def test_changes_section_changed_without_draft_edit_has_no_conflict(session, client, jwt):
    """Assert that a changed section the draft does not touch is listed without any conflict."""
    business = factory_business(IDENTIFIER, entity_type='BC')
    jane = _add_director(business)
    bob = _add_director(business, 'Bob', 'Lee')
    base_filing = factory_completed_filing(business, ANNUAL_REPORT)
    draft = _draft_cod(business, [_draft_director(jane.id, 'Jane', 'Smith', 'Victoria', actions=['EDITED'])],
                       base_filing.transaction_id)
    bob.delivery_address.city = 'Vancouver'
    bob.delivery_address.save()
    factory_completed_filing(business, ANNUAL_REPORT)

    rv = _get_changes(client, jwt, draft)

    assert rv.json['changedSections'] == ['parties']
    assert rv.json['conflicts'] == []
    assert rv.json['alreadyApplied'] == []


def test_changes_reports_business_changes(session, client, jwt):
    """Assert that legalName and state changes are {baseValue, currentValue} and unchanged fields are null."""
    business = factory_business(IDENTIFIER, entity_type='BC')
    base_filing = factory_completed_filing(business, ANNUAL_REPORT)
    draft = _draft_cod(business, [], base_filing.transaction_id)
    original_name = business.legal_name
    business.legal_name = 'RENAMED INC.'
    business.state = Business.State.HISTORICAL
    business.save()
    factory_completed_filing(business, ANNUAL_REPORT)

    rv = _get_changes(client, jwt, draft)

    assert rv.status_code == HTTPStatus.OK
    changes = rv.json['businessChanges']
    assert changes['legalName'] == {'baseValue': original_name, 'currentValue': 'RENAMED INC.'}
    assert changes['legalType'] is None
    assert changes['state']['baseValue'] != changes['state']['currentValue']


def test_changes_null_base_without_fallback_is_indeterminate(session, client, jwt):
    """Assert that a NULL-base draft with no resolvable fallback reports upToDate null and no conflicts."""
    business = factory_business(IDENTIFIER, entity_type='BC')
    person = _add_director(business)
    factory_completed_filing(business, ANNUAL_REPORT)
    # filed far in the past: no completed transaction predates it
    draft = _draft_cod(business, [_draft_director(person.id, 'Jane', 'Smith', 'Nanaimo', actions=['EDITED'])],
                       None, filing_date=datetime.now(UTC) - timedelta(days=365))

    rv = _get_changes(client, jwt, draft)

    assert rv.status_code == HTTPStatus.OK
    assert rv.json['upToDate'] is None
    assert rv.json['baseTransactionId'] is None
    assert rv.json['conflicts'] == []
    assert rv.json['interveningFilings'] == []


def test_changes_null_base_uses_fallback_transaction(session, client, jwt):
    """Assert that a NULL-base draft is rebased against the last completed transaction before its save."""
    business = factory_business(IDENTIFIER, entity_type='BC')
    base_filing = factory_completed_filing(business, ANNUAL_REPORT)
    draft = _draft_cod(business, [], None, filing_date=datetime.now(UTC) + timedelta(days=1))
    # completed filings stamped after the draft's filing_date cannot be simulated with the db clock,
    # so the fallback equals the watermark here
    rv = _get_changes(client, jwt, draft)

    assert rv.status_code == HTTPStatus.OK
    assert rv.json['baseTransactionId'] == base_filing.transaction_id
    assert rv.json['upToDate'] is True


@pytest.mark.parametrize('test_name,party_offset,expect_stale', [
    ('live-party', 0, False),
    ('missing-party', 987654, True),
])
def test_changes_populates_stale_ids(session, client, jwt, test_name, party_offset, expect_stale):
    """Assert that staleIds lists draft party ids that no longer exist on the business."""
    business = factory_business(IDENTIFIER, entity_type='BC')
    person = _add_director(business)
    base_filing = factory_completed_filing(business, ANNUAL_REPORT)
    party_id = person.id + party_offset
    draft = _draft_cod(business, [_draft_director(party_id, 'Jane', 'Smith', 'Victoria')],
                       base_filing.transaction_id)

    rv = _get_changes(client, jwt, draft)

    assert rv.status_code == HTTPStatus.OK
    assert rv.json['staleIds'] == {'parties': [party_id] if expect_stale else [],
                                   'nameTranslations': [], 'resolutions': []}
