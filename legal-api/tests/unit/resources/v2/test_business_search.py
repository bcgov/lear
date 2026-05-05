# Copyright © 2025 Province of British Columbia
#
# Licensed under the BSD 3 Clause License, (the "License");
# you may not use this file except in compliance with the License.
# The template for the license can be found here
#    https://opensource.org/license/bsd-3-clause/
#
# Redistribution and use in source and binary forms,
# with or without modification, are permitted provided that the
# following conditions are met:
#
# 1. Redistributions of source code must retain the above copyright notice,
#    this list of conditions and the following disclaimer.
#
# 2. Redistributions in binary form must reproduce the above copyright notice,
#    this list of conditions and the following disclaimer in the documentation
#    and/or other materials provided with the distribution.
#
# 3. Neither the name of the copyright holder nor the names of its contributors
#    may be used to endorse or promote products derived from this software
#    without specific prior written permission.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS “AS IS”
# AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO,
# THE IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE
# ARE DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT HOLDER OR CONTRIBUTORS BE
# LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR
# CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF
# SUBSTITUTE GOODS OR SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS
# INTERRUPTION) HOWEVER CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN
# CONTRACT, STRICT LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE)
# ARISING IN ANY WAY OUT OF THE USE OF THIS SOFTWARE, EVEN IF ADVISED OF THE
# POSSIBILITY OF SUCH DAMAGE.
"""Tests to assure the POST /api/v2/businesses/search endpoint.

Test-Suite to ensure that the /businesses/search endpoint is working as expected.
"""
import copy
from http import HTTPStatus

import pytest

from legal_api.models import Business, Filing, RegistrationBootstrap
from legal_api.services.authz import STAFF_ROLE, SYSTEM_ROLE
from registry_schemas.example_data import FILING_HEADER

from tests.unit.models import factory_business, factory_pending_filing
from tests.unit.services.utils import create_header


def _make_draft(identifier,
                filing_name='incorporationApplication',
                legal_type=Business.LegalTypes.BCOMP.value,
                nr_number=None,
                legal_name=None,
                status=Filing.Status.PENDING.value,
                filing_sub_type=None):
    """Create a RegistrationBootstrap and a linked pending draft filing."""
    temp_reg = RegistrationBootstrap()
    temp_reg._identifier = identifier
    temp_reg.save()

    json_data = copy.deepcopy(FILING_HEADER)
    json_data['filing']['header']['name'] = filing_name
    json_data['filing']['header']['identifier'] = identifier
    json_data['filing']['business'] = {
        'legalType': legal_type
    }
    json_data['filing'][filing_name] = {
        'nameRequest': {
            'legalType': legal_type
        }
    }
    if nr_number:
        json_data['filing'][filing_name]['nameRequest'].update({
            'nrNumber': nr_number,
            'legalName': legal_name or 'Draft Name',
        })
    if filing_sub_type:
        json_data['filing'][filing_name] = {
            'type': filing_sub_type
        }

    filing = factory_pending_filing(None, json_data)
    filing.temp_reg = identifier
    # Override the status if something other than PENDING is needed
    if status != Filing.Status.PENDING.value:
        filing._status = status
    filing.save()
    return filing


def test_search_filter_name(session, client, jwt):
    """Assert that the name filter returns only matching businesses and drafts."""
    # --- real businesses ---
    b_match = factory_business('BC1110001', entity_type=Business.LegalTypes.BCOMP.value)
    b_match.legal_name = 'Matching Corp'
    b_match.save()

    b_other = factory_business('BC1110002', entity_type=Business.LegalTypes.BCOMP.value)
    b_other.legal_name = 'Other Inc'
    b_other.save()

    # --- draft filings ---
    d_match = _make_draft('Tm001match', legal_name='Matching Draft', nr_number='NR 0000001')
    d_other = _make_draft('Tm002other', legal_name='NoMatch Draft', nr_number='NR 0000002')

    identifiers = ['BC1110001', 'BC1110002', 'Tm001match', 'Tm002other']
    rv = client.post('/api/v2/businesses/search',
                     json={'identifiers': identifiers, 'name': 'Matching'},
                     headers=create_header(jwt, [SYSTEM_ROLE]))

    assert rv.status_code == HTTPStatus.OK
    assert len(rv.json['businessEntities']) == 1
    assert rv.json['businessEntities'][0]['identifier'] == 'BC1110001'
    assert len(rv.json['draftEntities']) == 1
    assert rv.json['draftEntities'][0]['identifier'] == 'Tm001match'


def test_search_filter_identifier_substring(session, client, jwt):
    """Assert that the identifier filter matches businesses whose identifier contains the substring."""
    factory_business('BC1000001', entity_type=Business.LegalTypes.BCOMP.value)
    factory_business('BC1000002', entity_type=Business.LegalTypes.BCOMP.value)
    factory_business('BC9999999', entity_type=Business.LegalTypes.BCOMP.value)

    identifiers = ['BC1000001', 'BC1000002', 'BC9999999']
    rv = client.post('/api/v2/businesses/search',
                     json={'identifiers': identifiers, 'identifier': 'BC10000'},
                     headers=create_header(jwt, [SYSTEM_ROLE]))

    assert rv.status_code == HTTPStatus.OK
    assert len(rv.json['businessEntities']) == 2
    returned_ids = {b['identifier'] for b in rv.json['businessEntities']}
    assert returned_ids == {'BC1000001', 'BC1000002'}


def test_search_identifier_filter_matches_draft_nr_number(session, client, jwt):
    """Assert that the identifier filter matches draft filings by NR number substring
    and that supplying only temp identifiers produces no business entities."""
    identifier_filter = '1234567'
    nr_match = f'NR {identifier_filter}'
    nr_no_match = 'NR 9999999'
    temp_id_match = 'Tnr01match'
    temp_id_no_match = 'Tnr02other'
    regular_business_no_match = f'BC{identifier_filter}'

    _make_draft(temp_id_match, nr_number=nr_match, legal_name='Matching NR Name Inc.')
    _make_draft(temp_id_no_match, nr_number=nr_no_match, legal_name='Other NR Name Inc.')
    factory_business(regular_business_no_match, entity_type=Business.LegalTypes.BCOMP.value)

    rv = client.post(
        '/api/v2/businesses/search',
        json={
            'identifiers': [temp_id_match, temp_id_no_match],
            'identifier': identifier_filter
        },
        headers=create_header(jwt, [SYSTEM_ROLE]),
    )

    assert rv.status_code == HTTPStatus.OK
    # Only temp identifiers supplied — no real businesses should be returned
    assert rv.json['businessEntities'] == []
    # Only the draft whose NR number contains '1234567' should match
    draft_entities = rv.json['draftEntities']
    assert len(draft_entities) == 1
    assert draft_entities[0]['identifier'] == temp_id_match
    assert draft_entities[0]['nrNumber'] == nr_match


@pytest.mark.parametrize('test_name, type_filter,expected_bus_count,expected_draft_count', [
    ('BC_CP_filter',      ['BC', 'CP'], 2, 0),
    ('draft_type_filter', ['ATMP'],     0, 1),   # temp-only type → businessEntities empty
    ('BC_filter',         ['BC'],       1, 0),   # business-only → draftEntities empty
])
def test_search_filter_type(session, client, jwt, test_name, type_filter, expected_bus_count, expected_draft_count):
    """Assert that the type filter routes results to the correct entity list."""
    factory_business('BC2000001', entity_type=Business.LegalTypes.COMP.value)
    factory_business('CP2000002', entity_type=Business.LegalTypes.COOP.value)
    _make_draft('Ta001atmp',
                filing_name='amalgamationApplication',
                legal_type=Business.LegalTypes.COMP.value,
                filing_sub_type='regular')

    identifiers = ['BC2000001', 'CP2000002', 'Ta001atmp']
    rv = client.post('/api/v2/businesses/search',
                     json={'identifiers': identifiers, 'type': type_filter},
                     headers=create_header(jwt, [SYSTEM_ROLE]))

    assert rv.status_code == HTTPStatus.OK
    assert len(rv.json['businessEntities']) == expected_bus_count
    assert len(rv.json['draftEntities']) == expected_draft_count


@pytest.mark.parametrize('status_filter,expected_count', [
    (['ACTIVE'],     1),
    (['HISTORICAL'], 1),
    (['DRAFT'],      0),   # not a valid business state → early return, empty
])
def test_search_filter_status(session, client, jwt, status_filter, expected_count):
    """Assert that the status filter returns only businesses in the given state."""
    factory_business('BC3000001', entity_type=Business.LegalTypes.BCOMP.value,
                     state=Business.State.ACTIVE)
    factory_business('BC3000002', entity_type=Business.LegalTypes.BCOMP.value,
                     state=Business.State.HISTORICAL)

    identifiers = ['BC3000001', 'BC3000002']
    rv = client.post('/api/v2/businesses/search',
                     json={'identifiers': identifiers, 'status': status_filter},
                     headers=create_header(jwt, [SYSTEM_ROLE]))

    assert rv.status_code == HTTPStatus.OK
    assert len(rv.json['businessEntities']) == expected_count


@pytest.mark.parametrize('page,limit,expected_count,expected_has_more', [
    (1, 2, 2, True),
    (2, 2, 1, False),
    (1, 3, 3, False),
])
def test_search_pagination(session, client, jwt, page, limit, expected_count, expected_has_more):
    """Assert that page and limit parameters control result count and hasMore flag."""
    factory_business('BC4000001', entity_type=Business.LegalTypes.BCOMP.value)
    factory_business('BC4000002', entity_type=Business.LegalTypes.BCOMP.value)
    factory_business('BC4000003', entity_type=Business.LegalTypes.BCOMP.value)

    identifiers = ['BC4000001', 'BC4000002', 'BC4000003']
    rv = client.post('/api/v2/businesses/search',
                     json={'identifiers': identifiers, 'page': page, 'limit': limit},
                     headers=create_header(jwt, [SYSTEM_ROLE]))

    assert rv.status_code == HTTPStatus.OK
    assert len(rv.json['businessEntities']) == expected_count
    assert rv.json['hasMore'] == expected_has_more


@pytest.mark.parametrize('body,expected_status,check_message', [
    ({},                            HTTPStatus.BAD_REQUEST, True),
    ({'identifiers': 'BC123'},      HTTPStatus.BAD_REQUEST, True),
    ({'identifiers': []},           HTTPStatus.BAD_REQUEST, True),
    ({'identifiers': ['BC1234567']},HTTPStatus.OK,          False),
])
def test_search_invalid_identifiers(session, client, jwt, body, expected_status, check_message):
    """Assert that a missing or non-list identifiers body returns the correct response."""
    rv = client.post('/api/v2/businesses/search',
                     json=body,
                     headers=create_header(jwt, [SYSTEM_ROLE]))

    assert rv.status_code == expected_status
    if check_message:
        assert 'Expected a list' in rv.json['message']
    else:
        assert rv.json['businessEntities'] == []
        assert rv.json['draftEntities'] == []
        assert rv.json['hasMore'] is False


def test_search_sole_prop_alternate_names(session, client, jwt):
    """Assert that alternateNames key is present in the result for a SOLE_PROP business."""
    sp = factory_business('FM5000001', entity_type=Business.LegalTypes.SOLE_PROP.value)

    rv = client.post('/api/v2/businesses/search',
                     json={'identifiers': ['FM5000001']},
                     headers=create_header(jwt, [SYSTEM_ROLE]))

    assert rv.status_code == HTTPStatus.OK
    assert len(rv.json['businessEntities']) == 1
    entity = rv.json['businessEntities'][0]
    assert 'alternateNames' in entity


def test_search_withdrawn_drafts_excluded(session, client, jwt):
    """Assert that draft filings with WITHDRAWN status are excluded from unfiltered search results."""
    d_draft = _make_draft('Tw001draft', filing_name='incorporationApplication',
                          legal_type=Business.LegalTypes.BCOMP.value,
                          status=Filing.Status.PENDING.value)
    d_withdrawn = _make_draft('Tw002wthdn', filing_name='incorporationApplication',
                              legal_type=Business.LegalTypes.BCOMP.value,
                              status=Filing.Status.WITHDRAWN.value)

    identifiers = ['Tw001draft', 'Tw002wthdn']
    rv = client.post('/api/v2/businesses/search',
                     json={'identifiers': identifiers},
                     headers=create_header(jwt, [SYSTEM_ROLE]))

    assert rv.status_code == HTTPStatus.OK
    assert len(rv.json['draftEntities']) == 1
    assert rv.json['draftEntities'][0]['identifier'] == 'Tw001draft'


def test_search_500_internal_error(session, client, jwt, monkeypatch):
    """Assert that an unhandled exception returns a 500 with the expected error message."""
    factory_business('BC6000001', entity_type=Business.LegalTypes.BCOMP.value)

    def _raise(*args, **kwargs):
        raise Exception('boom')

    monkeypatch.setattr(
        'legal_api.resources.v2.business.business.BusinessSearchService.get_search_filtered_businesses_results',
        _raise
    )

    rv = client.post('/api/v2/businesses/search',
                     json={'identifiers': ['BC6000001']},
                     headers=create_header(jwt, [SYSTEM_ROLE]))

    assert rv.status_code == HTTPStatus.INTERNAL_SERVER_ERROR
    assert rv.json['error'] == 'Unable to retrieve businesses.'


def test_search_unauthorized_non_system_role(session, client, jwt):
    """Assert that a non-SYSTEM_ROLE token is rejected with 401."""
    rv = client.post('/api/v2/businesses/search',
                     json={'identifiers': ['BC1234567']},
                     headers=create_header(jwt, [STAFF_ROLE]))

    assert rv.status_code == HTTPStatus.UNAUTHORIZED
