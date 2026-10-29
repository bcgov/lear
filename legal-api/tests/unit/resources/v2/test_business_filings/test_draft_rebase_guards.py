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

"""Tests to assure the draft rebase guards on the business-filing end-points.

Test-Suite to ensure the draft stamping, base transaction, ownership and stale-id guards work as expected.
"""
import copy
from datetime import UTC, datetime, timedelta
from http import HTTPStatus
from unittest.mock import patch

import datedelta
import pytest

from business_model.models import Address, Filing, PartyRole, db
from legal_api.resources.v2.business.business_filings import business_filings
from legal_api.services import flags
from legal_api.services.authz import PUBLIC_USER, STAFF_ROLE, SYSTEM_ROLE
from registry_schemas.example_data import ANNUAL_REPORT
from tests.unit.models import (
    factory_business,
    factory_business_mailing_address,
    factory_completed_filing,
    factory_filing,
    factory_party_role,
)
from tests.unit.services.utils import create_header


DRAFT_REBASE_FEATURE = 'draftRebaseChecks'

ROLE_LOOKUP = {
    'staff': STAFF_ROLE,
    'system': SYSTEM_ROLE,
    'public': PUBLIC_USER,
}


def _mock_draft_rebase_flag(monkeypatch, enabled):
    """Mock the draftRebaseChecks value on and pin the permission flag off, delegating every other flag."""
    flag_is_on = flags.is_on
    flag_value = flags.value

    def _is_on(flag, *args, **kwargs):
        if flag == 'enable-permissions-for-action':
            return False
        return flag_is_on(flag, *args, **kwargs)

    def _value(flag, *args, **kwargs):
        if flag == 'enable-new-feature':
            features = [f for f in (flag_value(flag, *args, **kwargs) or []) if f != DRAFT_REBASE_FEATURE]
            return features + [DRAFT_REBASE_FEATURE] if enabled else features
        return flag_value(flag, *args, **kwargs)

    monkeypatch.setattr('legal_api.services.flags.is_on', _is_on)
    monkeypatch.setattr('legal_api.services.flags.value', _value)


def _mock_auth_edit(app, requests_mock, identifier):
    """Mock the auth response that lets a non-staff caller edit the business."""
    requests_mock.get(f"{app.config.get('AUTH_SVC_URL')}/entities/{identifier}/authorizations",
                      json={'roles': ['edit']})


def _ar_json(identifier):
    """Return an annual report body for the business."""
    ar = copy.deepcopy(ANNUAL_REPORT)
    ar['filing']['business']['identifier'] = identifier
    return ar


def _create_draft(business, submitter_roles=None, base_transaction_id=None, filing_date=None):
    """Create a DRAFT annual report with the given submitter side and base."""
    if filing_date:
        draft = factory_filing(business, copy.deepcopy(ANNUAL_REPORT), filing_date=filing_date)
    else:
        draft = factory_filing(business, copy.deepcopy(ANNUAL_REPORT))
    assert draft.status == Filing.Status.DRAFT.value
    draft.submitter_roles = submitter_roles
    draft.base_transaction_id = base_transaction_id
    draft.save()
    return draft


def _create_party(business, role_type=PartyRole.RoleTypes.DIRECTOR, cessation_date=None):
    """Create a party role on the business and return the party id."""
    delivery_address = Address(city='Test City', street='party Street', postal_code='T3S3T3', country='CA',
                               region='BC', address_type='delivery')
    mailing_address = Address(city='Test City', street='party Street', postal_code='T3S3T3', country='CA',
                              region='BC', address_type='mailing')
    officer = {
        'firstName': 'tester',
        'lastName': 'test',
        'middleInitial': '',
        'partyType': 'person',
        'organizationName': ''
    }
    party_role = factory_party_role(delivery_address, mailing_address, officer,
                                    datetime.now() - datedelta.YEAR, cessation_date, role_type)
    party_role.save()
    business.party_roles.append(party_role)
    business.save()
    return party_role.party_id


def _reload(filing_id):
    """Return the filing as stored in the database."""
    db.session.expire_all()
    return Filing.find_by_id(filing_id)


# ---------------------------------------------------------------------------
# stamping
# ---------------------------------------------------------------------------

@pytest.mark.parametrize('test_name, role, expected_roles', [
    ('staff', 'staff', 'staff'),
    ('system', 'system', 'system'),
    ('public', 'public', 'public_user'),
])
def test_post_draft_stamps_submitter_and_base(app, session, client, jwt, monkeypatch, requests_mock,
                                              test_name, role, expected_roles):
    """Assert that a new draft is stamped with the submitter side and the business's watermark."""
    _mock_draft_rebase_flag(monkeypatch, True)
    identifier = 'CP7654321'
    business = factory_business(identifier)
    completed = factory_completed_filing(business, copy.deepcopy(ANNUAL_REPORT),
                                         filing_date=datetime(2019, 8, 5, 7, 7, 58, 272362))
    watermark = Filing.get_max_completed_transaction_id(business.id)
    assert watermark == completed.transaction_id
    _mock_auth_edit(app, requests_mock, identifier)

    with patch.object(business_filings, 'is_allowed', return_value=True):
        rv = client.post(f'/api/v2/businesses/{identifier}/filings?draft=true',
                         json=_ar_json(identifier),
                         headers=create_header(jwt, [ROLE_LOOKUP[role]], identifier))

    assert rv.status_code == HTTPStatus.CREATED
    filing = _reload(rv.json['filing']['header']['filingId'])
    assert filing.submitter_roles == expected_roles
    assert filing.base_transaction_id == watermark


def test_post_draft_base_is_none_without_completed_filing(app, session, client, jwt, monkeypatch):
    """Assert that the draft base stays None when the business has no completed filing."""
    _mock_draft_rebase_flag(monkeypatch, True)
    identifier = 'CP7654321'
    business = factory_business(identifier)
    assert Filing.get_max_completed_transaction_id(business.id) is None

    with patch.object(business_filings, 'is_allowed', return_value=True):
        rv = client.post(f'/api/v2/businesses/{identifier}/filings?draft=true',
                         json=_ar_json(identifier),
                         headers=create_header(jwt, [STAFF_ROLE], identifier))

    assert rv.status_code == HTTPStatus.CREATED
    filing = _reload(rv.json['filing']['header']['filingId'])
    assert filing.submitter_roles == 'staff'
    assert filing.base_transaction_id is None


# ---------------------------------------------------------------------------
# NULL-base freeze and explicit baseTransactionId
# ---------------------------------------------------------------------------

def test_put_draft_freezes_null_base_from_fallback(app, session, client, jwt, monkeypatch):
    """Assert that a plain PUT on a NULL-base draft stamps the fallback base before the save moves filing_date."""
    from legal_api.services.draft_rebase import DraftRebaseService

    _mock_draft_rebase_flag(monkeypatch, False)
    identifier = 'CP7654321'
    business = factory_business(identifier)
    completed = factory_completed_filing(business, copy.deepcopy(ANNUAL_REPORT),
                                         filing_date=datetime(2019, 8, 5, 7, 7, 58, 272362))
    draft = _create_draft(business, 'staff', None, filing_date=datetime.now(UTC) + timedelta(days=1))
    expected_base = DraftRebaseService.fallback_base_transaction_id(business, draft)
    assert expected_base == completed.transaction_id

    with patch.object(business_filings, 'is_allowed', return_value=True):
        rv = client.put(f'/api/v2/businesses/{identifier}/filings/{draft.id}?draft=true',
                        json=_ar_json(identifier),
                        headers=create_header(jwt, [STAFF_ROLE], identifier))

    assert rv.status_code == HTTPStatus.ACCEPTED
    assert _reload(draft.id).base_transaction_id == completed.transaction_id


def test_put_draft_with_matching_base_transaction_id_advances_base(app, session, client, jwt, monkeypatch):
    """Assert that a PUT with baseTransactionId equal to the watermark is accepted and sets the base."""
    _mock_draft_rebase_flag(monkeypatch, False)
    identifier = 'CP7654321'
    business = factory_business(identifier)
    factory_completed_filing(business, copy.deepcopy(ANNUAL_REPORT),
                             filing_date=datetime(2019, 8, 5, 7, 7, 58, 272362))
    watermark = Filing.get_max_completed_transaction_id(business.id)
    draft = _create_draft(business, 'staff', None)

    with patch.object(business_filings, 'is_allowed', return_value=True):
        rv = client.put(f'/api/v2/businesses/{identifier}/filings/{draft.id}?draft=true&baseTransactionId={watermark}',
                        json=_ar_json(identifier),
                        headers=create_header(jwt, [STAFF_ROLE], identifier))

    assert rv.status_code == HTTPStatus.ACCEPTED
    assert _reload(draft.id).base_transaction_id == watermark


def test_put_draft_with_stale_base_transaction_id_conflicts(app, session, client, jwt, monkeypatch):
    """Assert that a PUT with a baseTransactionId that is not the watermark is rejected with a 409."""
    _mock_draft_rebase_flag(monkeypatch, False)
    identifier = 'CP7654321'
    business = factory_business(identifier)
    factory_completed_filing(business, copy.deepcopy(ANNUAL_REPORT),
                             filing_date=datetime(2019, 8, 5, 7, 7, 58, 272362))
    watermark = Filing.get_max_completed_transaction_id(business.id)
    sent_base = watermark - 1
    draft = _create_draft(business, 'staff', None)

    with patch.object(business_filings, 'is_allowed', return_value=True):
        rv = client.put(f'/api/v2/businesses/{identifier}/filings/{draft.id}?draft=true&baseTransactionId={sent_base}',
                        json=_ar_json(identifier),
                        headers=create_header(jwt, [STAFF_ROLE], identifier))

    assert rv.status_code == HTTPStatus.CONFLICT
    assert rv.json['baseTransactionId'] == sent_base
    assert rv.json['currentTransactionId'] == watermark
    assert rv.json['errors'][0]['message']


# ---------------------------------------------------------------------------
# draft ownership
# ---------------------------------------------------------------------------

OWNERSHIP_CASES = [
    ('staff_on_user_draft', 'staff', 'public_user', True, True),
    ('public_on_staff_draft', 'public', 'staff', True, True),
    ('system_on_user_draft', 'system', 'public_user', True, True),
    ('public_on_system_draft', 'public', 'system', True, True),
    ('staff_on_staff_draft', 'staff', 'staff', True, False),
    ('system_on_staff_draft', 'system', 'staff', True, False),
    ('staff_on_system_draft', 'staff', 'system', True, False),
    ('public_on_user_draft', 'public', 'public_user', True, False),
    ('staff_on_unowned_draft', 'staff', None, True, False),
    ('public_on_unowned_draft', 'public', None, True, False),
    ('flag_off_staff_on_user_draft', 'staff', 'public_user', False, False),
    ('flag_off_public_on_staff_draft', 'public', 'staff', False, False),
]


@pytest.mark.parametrize('test_name, caller, draft_roles, flag_on, expect_forbidden', OWNERSHIP_CASES)
def test_put_draft_ownership(app, session, client, jwt, monkeypatch, requests_mock,
                             test_name, caller, draft_roles, flag_on, expect_forbidden):
    """Assert that a PUT is rejected only when the caller and the draft are on opposite staff/user sides."""
    _mock_draft_rebase_flag(monkeypatch, flag_on)
    identifier = 'CP7654321'
    business = factory_business(identifier)
    draft = _create_draft(business, draft_roles)
    _mock_auth_edit(app, requests_mock, identifier)

    with patch.object(business_filings, 'is_allowed', return_value=True):
        rv = client.put(f'/api/v2/businesses/{identifier}/filings/{draft.id}?draft=true',
                        json=_ar_json(identifier),
                        headers=create_header(jwt, [ROLE_LOOKUP[caller]], identifier))

    if expect_forbidden:
        assert rv.status_code == HTTPStatus.FORBIDDEN
        assert rv.json['errorCode'] == 'DRAFT_FILING_VIEW_ONLY'
    else:
        assert rv.status_code == HTTPStatus.ACCEPTED


@pytest.mark.parametrize('test_name, caller, draft_roles, flag_on, expect_forbidden', OWNERSHIP_CASES)
def test_delete_draft_ownership(app, session, client, jwt, monkeypatch, requests_mock,
                                test_name, caller, draft_roles, flag_on, expect_forbidden):
    """Assert that a DELETE is rejected only when the caller and the draft are on opposite staff/user sides."""
    _mock_draft_rebase_flag(monkeypatch, flag_on)
    identifier = 'CP7654321'
    business = factory_business(identifier)
    draft = _create_draft(business, draft_roles)
    draft_id = draft.id
    _mock_auth_edit(app, requests_mock, identifier)

    rv = client.delete(f'/api/v2/businesses/{identifier}/filings/{draft_id}',
                       headers=create_header(jwt, [ROLE_LOOKUP[caller]], identifier))

    if expect_forbidden:
        assert rv.status_code == HTTPStatus.FORBIDDEN
        assert rv.json['errorCode'] == 'DRAFT_FILING_VIEW_ONLY'
        assert _reload(draft_id) is not None
    else:
        assert rv.status_code == HTTPStatus.OK
        assert _reload(draft_id) is None


# ---------------------------------------------------------------------------
# stale-id guard
# ---------------------------------------------------------------------------

def _stale_id_json(identifier, filing_type, section, party_ids, legal_type):
    """Return a minimal submission whose party rows carry the given officer ids."""
    return {
        'filing': {
            'header': {
                'name': filing_type,
                'date': '2021-05-06',
                'certifiedBy': 'full name',
                'email': 'no_one@never.get'
            },
            'business': {'identifier': identifier, 'legalType': legal_type},
            filing_type: {section: [{'officer': {'id': party_id}} for party_id in party_ids]}
        }
    }


def _submit_for_validation(client, jwt, identifier, filing_json):
    """Submit (not draft) with validation stubbed out, stopping after the stale-id guard."""
    with patch.object(business_filings, 'is_allowed', return_value=True), \
            patch.object(business_filings, 'validate', return_value=None):
        return client.post(f'/api/v2/businesses/{identifier}/filings?only_validate=true',
                           json=filing_json,
                           headers=create_header(jwt, [STAFF_ROLE], identifier))


def test_stale_id_guard_rejects_missing_party_on_change_of_registration(app, session, client, jwt, monkeypatch):
    """Assert that a changeOfRegistration referencing an unknown officer id is rejected with per-path errors."""
    _mock_draft_rebase_flag(monkeypatch, True)
    identifier = 'FM1234567'
    factory_business(identifier, entity_type='SP')
    filing_json = _stale_id_json(identifier, 'changeOfRegistration', 'parties', [999999999], 'SP')

    rv = _submit_for_validation(client, jwt, identifier, filing_json)

    assert rv.status_code == HTTPStatus.BAD_REQUEST
    assert rv.json['errors'][0]['path'] == '/filing/changeOfRegistration/parties'
    assert '999999999' in rv.json['errors'][0]['error']


def test_stale_id_guard_skipped_when_flag_off(app, session, client, jwt, monkeypatch):
    """Assert that the stale-id guard does not reject the submission when the flag is off."""
    _mock_draft_rebase_flag(monkeypatch, False)
    identifier = 'FM1234567'
    factory_business(identifier, entity_type='SP')
    filing_json = _stale_id_json(identifier, 'changeOfRegistration', 'parties', [999999999], 'SP')

    rv = _submit_for_validation(client, jwt, identifier, filing_json)

    assert rv.status_code == HTTPStatus.OK


def test_stale_id_guard_passes_live_party_on_change_of_registration(app, session, client, jwt, monkeypatch):
    """Assert that a changeOfRegistration referencing a live officer id passes the guard."""
    _mock_draft_rebase_flag(monkeypatch, True)
    identifier = 'FM1234567'
    business = factory_business(identifier, entity_type='SP')
    party_id = _create_party(business, PartyRole.RoleTypes.PARTNER)
    filing_json = _stale_id_json(identifier, 'changeOfRegistration', 'parties', [party_id], 'SP')

    rv = _submit_for_validation(client, jwt, identifier, filing_json)

    assert rv.status_code == HTTPStatus.OK


def test_stale_id_guard_change_of_directors_rejects_ceased_director(app, session, client, jwt, monkeypatch):
    """Assert that changeOfDirectors treats a ceased director id as stale."""
    _mock_draft_rebase_flag(monkeypatch, True)
    identifier = 'CP7654321'
    business = factory_business(identifier)
    ceased_id = _create_party(business, cessation_date=datetime.now() - datedelta.MONTH)
    filing_json = _stale_id_json(identifier, 'changeOfDirectors', 'directors', [ceased_id], 'CP')

    rv = _submit_for_validation(client, jwt, identifier, filing_json)

    assert rv.status_code == HTTPStatus.BAD_REQUEST
    assert rv.json['errors'][0]['path'] == '/filing/changeOfDirectors/parties'


def test_stale_id_guard_change_of_directors_passes_active_director(app, session, client, jwt, monkeypatch):
    """Assert that changeOfDirectors accepts an active director id."""
    _mock_draft_rebase_flag(monkeypatch, True)
    identifier = 'CP7654321'
    business = factory_business(identifier)
    active_id = _create_party(business)
    filing_json = _stale_id_json(identifier, 'changeOfDirectors', 'directors', [active_id], 'CP')

    rv = _submit_for_validation(client, jwt, identifier, filing_json)

    assert rv.status_code == HTTPStatus.OK


def test_stale_id_guard_correction_accepts_ceased_party(app, session, client, jwt, monkeypatch):
    """Assert that a correction only needs the party to exist, so a ceased party id passes."""
    _mock_draft_rebase_flag(monkeypatch, True)
    identifier = 'CP7654321'
    business = factory_business(identifier)
    ceased_id = _create_party(business, cessation_date=datetime.now() - datedelta.MONTH)
    filing_json = _stale_id_json(identifier, 'correction', 'parties', [ceased_id], 'CP')

    rv = _submit_for_validation(client, jwt, identifier, filing_json)

    assert rv.status_code == HTTPStatus.OK


def test_stale_id_guard_ignores_filing_types_outside_section_map(app, session, client, jwt, monkeypatch):
    """Assert that the guard does not apply to filing types without rebaseable sections."""
    _mock_draft_rebase_flag(monkeypatch, True)
    identifier = 'CP7654321'
    factory_business(identifier)
    filing_json = _ar_json(identifier)

    rv = _submit_for_validation(client, jwt, identifier, filing_json)

    assert rv.status_code == HTTPStatus.OK


# ---------------------------------------------------------------------------
# 403 blockers detail
# ---------------------------------------------------------------------------

def test_forbidden_filing_lists_business_blockers(app, session, client, jwt, monkeypatch):
    """Assert that a rejected filing returns the active business blockers in the 403 body."""
    _mock_draft_rebase_flag(monkeypatch, True)
    identifier = 'CP7654321'
    business = factory_business(identifier,
                                founding_date=(datetime.now(UTC) - datedelta.YEAR))
    factory_business_mailing_address(business)
    pending = factory_filing(business, copy.deepcopy(ANNUAL_REPORT))
    pending.payment_token = 2
    pending.save()
    assert pending.status == Filing.Status.PENDING.value

    rv = client.post(f'/api/v2/businesses/{identifier}/filings?draft=true',
                     json=_ar_json(identifier),
                     headers=create_header(jwt, [STAFF_ROLE], identifier))

    assert rv.status_code == HTTPStatus.FORBIDDEN
    assert isinstance(rv.json['blockers'], list)
    assert 'DEFAULT' in rv.json['blockers']
    assert 'DRAFT_PENDING' in rv.json['blockers']
    assert 'BUSINESS_FROZEN' not in rv.json['blockers']
