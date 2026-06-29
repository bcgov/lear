# Copyright © 2024 Province of British Columbia
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
"""Tests for helpers in business_emailer.email_processors package __init__."""
import pytest
import requests_mock

from business_model.models import Business

from unittest.mock import patch

from business_emailer.email_processors import (
    get_account_by_affiliated_identifier,
    get_entity_dashboard_url,
    get_filled_template,
    get_org_id_for_temp_identifier,
    get_party_emails,
    get_recipient_from_auth,
    get_recipients,
    get_subject,
    substitute_template_parts,
)


@pytest.fixture
def auth_url(app):
    """Set AUTH_URL / AUTH_WEB_URL to dummy values for the duration of a test."""
    original_api = app.config.get('AUTH_URL')
    original_web = app.config.get('AUTH_WEB_URL')
    app.config['AUTH_URL'] = 'https://auth-api-url'
    app.config['AUTH_WEB_URL'] = 'https://auth-web-url/'
    yield app.config['AUTH_URL']
    app.config['AUTH_URL'] = original_api
    app.config['AUTH_WEB_URL'] = original_web


def test_get_account_by_affiliated_identifier_returns_json(app, auth_url):
    """Assert the affiliated-account JSON is returned when the auth response is valid JSON."""
    identifier = 'BC1234567'
    token = 'token'
    expected = {'orgs': [{'id': 42, 'name': 'Acme'}]}
    url = f'{auth_url}/orgs?affiliation={identifier}'

    with app.app_context(), requests_mock.Mocker() as m:
        m.get(url, json=expected, status_code=200)
        result = get_account_by_affiliated_identifier(identifier, token)

        assert result == expected
        assert m.last_request.headers['Authorization'] == f'Bearer {token}'
        assert m.last_request.headers['Accept'] == 'application/json'


def test_get_account_by_affiliated_identifier_returns_none_on_bad_json(app, auth_url):
    """Assert None is returned when the auth response body is not valid JSON."""
    identifier = 'BC1234567'
    url = f'{auth_url}/orgs?affiliation={identifier}'

    with app.app_context(), requests_mock.Mocker() as m:
        m.get(url, text='not json', status_code=200)
        result = get_account_by_affiliated_identifier(identifier, 'token')

        assert result is None


def test_get_org_id_for_temp_identifier_returns_first_org_id(app, auth_url):
    """Assert the first org id is returned when orgs are present."""
    identifier = 'T12345'
    url = f'{auth_url}/orgs?affiliation={identifier}'

    with app.app_context(), requests_mock.Mocker() as m:
        m.get(url, json={'orgs': [{'id': 99}, {'id': 100}]}, status_code=200)
        assert get_org_id_for_temp_identifier(identifier, 'token') == 99


@pytest.mark.parametrize('identifier,response_json', [
    ('T12345', {'orgs': []}),
    ('BC1234567', {'orgs': []}),
    ('T12345', {}),
])
def test_get_org_id_for_temp_identifier_raises_when_no_orgs(app, auth_url, identifier, response_json):
    """Assert Exception is raised when orgs are missing or empty (both T and non-T identifiers)."""
    url = f'{auth_url}/orgs?affiliation={identifier}'

    with app.app_context(), requests_mock.Mocker() as m:
        m.get(url, json=response_json, status_code=200)
        with pytest.raises(Exception):
            get_org_id_for_temp_identifier(identifier, 'token')


def test_get_entity_dashboard_url_non_temp_uses_dashboard_url(app, auth_url, config):
    """Assert non-temp identifiers return DASHBOARD_URL + identifier and make no HTTP calls."""
    identifier = 'BC1234567'
    with app.app_context(), requests_mock.Mocker() as m:
        url = get_entity_dashboard_url(identifier, 'token')
        assert url == config.get('DASHBOARD_URL') + identifier
        assert m.call_count == 0


def test_get_entity_dashboard_url_temp_uses_auth_web_url(app, auth_url):
    """Assert temp identifiers resolve to AUTH_WEB_URL + account/<org_id>/business."""
    identifier = 'T12345'
    orgs_url = f'{auth_url}/orgs?affiliation={identifier}'

    with app.app_context(), requests_mock.Mocker() as m:
        m.get(orgs_url, json={'orgs': [{'id': 77}]}, status_code=200)
        url = get_entity_dashboard_url(identifier, 'token')
        assert url == 'https://auth-web-url/account/77/business'


def test_substitute_template_parts_md_replaces_footer_marker(app):
    """Assert that substitute_template_parts with file_type='md' replaces [[business-registry-footer.md]]."""
    template = "Hello\n[[business-registry-footer.md]]\nEnd"
    with app.app_context():
        result = substitute_template_parts(template, "md")
    assert '[[business-registry-footer.md]]' not in result
    assert 'BC Registries and Digital Services' in result


def test_substitute_template_parts_md_replaces_all_md_parts(app):
    """Assert that substitute_template_parts with file_type='md' replaces all five markdown common parts."""
    template = (
        "[[attachments.md]]\n"
        "[[business-number.md]]\n"
        "[[business-registry-footer.md]]\n"
        "[[business-tombstone.md]]\n"
        "[[what-happens-next.md]]"
    )
    with app.app_context():
        result = substitute_template_parts(template, "md")
    for marker in [
        '[[attachments.md]]',
        '[[business-number.md]]',
        '[[business-registry-footer.md]]',
        '[[business-tombstone.md]]',
        '[[what-happens-next.md]]',
    ]:
        assert marker not in result


def test_substitute_template_parts_html_does_not_replace_md_markers(app):
    """Assert that substitute_template_parts with file_type='html' does not replace .md markers."""
    template = "[[business-registry-footer.md]]"
    with app.app_context():
        result = substitute_template_parts(template, "html")
    # html mode should not touch .md markers
    assert '[[business-registry-footer.md]]' in result


def test_get_filled_template_non_future(app):
    """Assert that get_filled_template returns the non-future incorporationApplication.md template."""
    with app.app_context():
        result = get_filled_template('incorporationApplication', is_future_effective_paid=False)
    assert result is not None
    # The non-future template has this heading
    assert 'successfully incorporated' in result
    # All markers are substituted
    assert '[[' not in result


@pytest.mark.parametrize('is_future_effective_paid', [(True), (False)])
def test_get_subject_with_real_business_name(app, is_future_effective_paid):
    """Assert that get_subject with a real name returns as expected."""
    with app.app_context():
        subject = get_subject(
            is_future_effective_paid=is_future_effective_paid,
            business_name='Acme Corp',
            legal_type='BC',
            filing_name='Incorporation Application',
            filing_name_short='Incorporation',
        )
    if is_future_effective_paid:
        assert subject == 'Acme Corp - Incorporation Application Filed'
    else:
        assert subject == 'Acme Corp - Successful Incorporation'


@pytest.mark.parametrize('business_name,legal_type', [
    ('', 'BC'),
    ('Not Available', 'BC'),
    ('', 'BEN'),
    ('Not Available', 'BEN'),
    ('', 'ULC'),
    ('Not Available', 'ULC'),
    ('', 'CC'),
    ('Not Available', 'CC'),
])
def test_get_subject_numbered_company(app, business_name, legal_type):
    """Assert that get_subject with no real name uses the numbered description."""
    with app.app_context():
        subject = get_subject(
            is_future_effective_paid=True,
            business_name=business_name,
            legal_type=legal_type,
            filing_name='Incorporation Application',
            filing_name_short='Incorporation',
        )
    expected_description = Business.BUSINESSES[Business.LegalTypes(legal_type)]['numberedDescription']
    assert subject == f'{expected_description} - Incorporation Application Filed'



# ---------------------------------------------------------------------------
# get_party_emails
# ---------------------------------------------------------------------------

def test_get_party_emails_returns_email_for_matching_role(app):
    """Assert that get_party_emails returns the officer email for a party with a matching role."""
    parties = [
        {
            'officer': {'email': 'joe@example.com'},
            'roles': [{'roleType': 'Completing Party'}, {'roleType': 'Proprietor'}]
        }
    ]
    with app.app_context():
        result = get_party_emails(parties, ['Completing Party', 'Partner', 'Proprietor'])
    assert result == ['joe@example.com']


def test_get_party_emails_break_after_first_match_per_party(app):
    """Assert that get_party_emails adds only one email per party even when multiple roles match."""
    parties = [
        {
            'officer': {'email': 'joe@example.com'},
            'roles': [{'roleType': 'Completing Party'}, {'roleType': 'Partner'}]
        }
    ]
    with app.app_context():
        result = get_party_emails(parties, ['Completing Party', 'Partner'])
    assert result == ['joe@example.com']
    assert len(result) == 1


def test_get_party_emails_skips_non_matching_role(app):
    """Assert that get_party_emails returns an empty list when no party role matches."""
    parties = [
        {
            'officer': {'email': 'joe@example.com'},
            'roles': [{'roleType': 'Director'}]
        }
    ]
    with app.app_context():
        result = get_party_emails(parties, ['Completing Party', 'Partner', 'Proprietor'])
    assert result == []


def test_get_party_emails_includes_none_when_party_has_no_email(app):
    """Assert that get_party_emails does not append when a matching party has no email field."""
    parties = [
        {
            'officer': {},
            'roles': [{'roleType': 'Completing Party'}]
        }
    ]
    with app.app_context():
        result = get_party_emails(parties, ['Completing Party'])
    assert result == []


def test_get_party_emails_multiple_parties_each_contribute_one_email(app):
    """Assert that get_party_emails collects one email per matching party."""
    parties = [
        {
            'officer': {'email': 'joe@example.com'},
            'roles': [{'roleType': 'Partner'}]
        },
        {
            'officer': {'email': 'jane@example.com'},
            'roles': [{'roleType': 'Partner'}]
        }
    ]
    with app.app_context():
        result = get_party_emails(parties, ['Partner'])
    assert 'joe@example.com' in result
    assert 'jane@example.com' in result
    assert len(result) == 2


# ---------------------------------------------------------------------------
# get_recipients
# ---------------------------------------------------------------------------

def _make_filing_json(filing_type, header_name=None, contact_email='contact@example.com',
                      parties=None, business_identifier=None):
    """Build a minimal filing_json dict for get_recipients tests."""
    header_name = header_name if header_name is not None else filing_type
    filing_data = {}
    if contact_email is not None:
        filing_data['contactPoint'] = {'email': contact_email}
    elif contact_email is None:
        pass  # omit contactPoint entirely
    if parties is not None:
        filing_data['parties'] = parties
    result = {
        'filing': {
            'header': {'name': header_name},
            filing_type: filing_data,
        }
    }
    if business_identifier:
        result['filing']['business'] = {'identifier': business_identifier}
    return result


def test_get_recipients_returns_contact_point_email(app):
    """Assert that get_recipients returns the contactPoint email when no parties match."""
    filing_json = _make_filing_json(
        'incorporationApplication',
        parties=[{'officer': {'email': 'other@example.com'}, 'roles': [{'roleType': 'Director'}]}]
    )
    with app.app_context():
        result = get_recipients('PAID', filing_json)
    assert result == 'contact@example.com'


def test_get_recipients_appends_party_emails_when_header_matches(app):
    """Assert that party emails are appended when header.name matches filing_type."""
    filing_json = _make_filing_json(
        'incorporationApplication',
        parties=[{'officer': {'email': 'comp@example.com'}, 'roles': [{'roleType': 'Completing Party'}]}]
    )
    with app.app_context():
        result = get_recipients('PAID', filing_json)
    assert 'contact@example.com' in result
    assert 'comp@example.com' in result


def test_get_recipients_mras_option_excludes_party_emails(app):
    """Assert that party emails are not appended when option is 'mras'."""
    filing_json = _make_filing_json(
        'incorporationApplication',
        parties=[{'officer': {'email': 'comp@example.com'}, 'roles': [{'roleType': 'Completing Party'}]}]
    )
    with app.app_context():
        result = get_recipients('mras', filing_json)
    assert result == 'contact@example.com'
    assert 'comp@example.com' not in result


def test_get_recipients_header_mismatch_excludes_party_emails(app):
    """Assert that party emails are not appended when header.name differs from filing_type."""
    filing_json = _make_filing_json(
        'incorporationApplication',
        header_name='someOtherFiling',
        parties=[{'officer': {'email': 'comp@example.com'}, 'roles': [{'roleType': 'Completing Party'}]}]
    )
    with app.app_context():
        result = get_recipients('PAID', filing_json)
    assert result == 'contact@example.com'
    assert 'comp@example.com' not in result


def test_get_recipients_missing_contact_point_coalesced_to_empty_string(app):
    """Assert that a missing contactPoint email is coalesced to an empty string (not None)."""
    filing_json = {
        'filing': {
            'header': {'name': 'incorporationApplication'},
            'incorporationApplication': {
                'parties': []
            }
        }
    }
    with app.app_context():
        result = get_recipients('PAID', filing_json)
    # recipients starts as "" when contactPoint is absent; no parties, so stays ""
    assert result == ''


def test_get_recipients_coop_identifier_skips_auth_call(app):
    """Assert that CP (coop) identifiers return empty string without calling get_recipient_from_auth."""
    filing_json = {
        'filing': {
            'header': {'name': 'annualReport'},
            'business': {'identifier': 'CP1234567'},
        }
    }
    with app.app_context():
        with patch('business_emailer.email_processors.get_recipient_from_auth') as mock_auth:
            result = get_recipients('COMPLETED', filing_json, token='token', filing_type='annualReport')
    assert result == ''
    mock_auth.assert_not_called()


def test_get_recipients_non_coop_identifier_calls_get_recipient_from_auth(app):
    """Assert that non-coop identifiers call get_recipient_from_auth for the business email."""
    filing_json = {
        'filing': {
            'header': {'name': 'annualReport'},
            'business': {'identifier': 'BC1234567'},
        }
    }
    with app.app_context():
        with patch('business_emailer.email_processors.get_recipient_from_auth',
                   return_value='auth@example.com') as mock_auth:
            result = get_recipients('COMPLETED', filing_json, token='token', filing_type='annualReport')
    assert result == 'auth@example.com'
    mock_auth.assert_called_once_with('BC1234567', 'token')


def test_get_recipients_uses_incorporationapplication_as_default_filing_type(app):
    """Assert that filing_type defaults to 'incorporationApplication' when not provided."""
    filing_json = {
        'filing': {
            'header': {'name': 'incorporationApplication'},
            'incorporationApplication': {
                'contactPoint': {'email': 'default@example.com'},
                'parties': []
            }
        }
    }
    with app.app_context():
        result = get_recipients('PAID', filing_json)
    assert result == 'default@example.com'
