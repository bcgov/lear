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
"""Tests for BusinessDocument._set_officers and _set_warning.

Follows the pattern from tests/unit/services/test_pdf_service.py by
using the app test_request_context and light-weight assertions without heavy mocking frameworks.
"""
from datetime import datetime

import pytest

from legal_api.reports.business_document import BusinessDocument
from legal_api.services import flags
from legal_api.services.request_context import RequestContext
from tests.unit.models import (
    factory_business,
    factory_business_mailing_address,
    factory_filing,
)
from tests.unit.services.utils import create_header
from legal_api.services.authz import STAFF_ROLE


@pytest.mark.parametrize(
    'ff_enabled', [True, False]
)
def test_set_officers_flag_and_extraction(session, app, jwt, monkeypatch, ff_enabled):
    """Assert that officers are only included when the feature flag is enabled and
    that only parties with an OFFICER role are returned with formatted addresses.
    """
    identifier = 'BC1234567'
    entity_type = 'BC'
    document_name = 'summary'

    # Build a simple parties payload the resource would normally return
    parties_payload = {
        'parties': [
            {
                'officer': {'firstName': 'Olive', 'lastName': 'Officer'},
                'roles': [{'roleType': 'Completer', 'roleClass': 'COMPLETER'}, {'roleType': 'Officer', 'roleClass': 'OFFICER'}],
                'mailingAddress': {
                    'streetAddress': '123 Any', 'addressCity': 'Victoria', 'addressRegion': 'BC', 'postalCode': 'V8V8V8',
                    'addressCountry': 'CA'
                },
                'deliveryAddress': {
                    'streetAddress': '456 Else', 'addressCity': 'Victoria', 'addressRegion': 'BC', 'postalCode': 'V8V8V8',
                    'addressCountry': 'CA'
                }
            },
            {
                'officer': {'firstName': 'Nora', 'lastName': 'NotOfficer'},
                'roles': [{'roleType': 'Incorporator', 'roleClass': 'INCORPORATOR'}],
                'mailingAddress': {
                    'streetAddress': '789 None', 'addressCity': 'Vancouver', 'addressRegion': 'BC', 'postalCode': 'V7Y1K8',
                    'addressCountry': 'CA'
                }
            }
        ]
    }

    # monkeypatch get_parties used by BusinessDocument to return our payload
    # Patch the symbol imported in business_document module so the call uses our payload
    import legal_api.reports.business_document as bd_module
    monkeypatch.setattr(bd_module, 'get_parties', lambda identifier: type('Resp', (), {'json': parties_payload}))

    # monkeypatch feature flag
    def fake_flag(name, user=None, account_id=None):
        if name == 'enable-officers-business-summary':
            return ff_enabled
        # default other flags
        return False

    monkeypatch.setattr(flags, 'is_on', fake_flag)

    request_ctx = app.test_request_context(headers=create_header(jwt, [STAFF_ROLE], identifier))
    with request_ctx:
        business = factory_business(identifier=identifier, entity_type=entity_type)
        factory_business_mailing_address(business)

        # Provide request_context explicitly to BusinessDocument (used by flag gates)
        bd = BusinessDocument(business, document_name, request_context=RequestContext(user='user', account_id='acc'))
        template_data = bd._get_template_data()  # pylint: disable=protected-access

        if ff_enabled:
            assert 'officers' in template_data
            assert len(template_data['officers']) == 1
            officer = template_data['officers'][0]
            # Ensure address fields are normalized and country expanded by _format_address
            assert officer['mailingAddress']['addressCountryDescription']
            assert officer.get('deliveryAddress')
        else:
            # When flag is off, officers key should still exist but be empty or not present depending on logic
            # Current implementation returns early without setting key
            assert 'officers' not in template_data


def test_set_warning_text_from_backfill_cutoff(session, app, jwt):
    """Assert that _set_warning adds the warning_text when backfill_cutoff_filing_id is set."""
    identifier = 'BC7654321'
    entity_type = 'BEN'
    document_name = 'summary'

    request_ctx = app.test_request_context(headers=create_header(jwt, [STAFF_ROLE], identifier))
    with request_ctx:
        business = factory_business(identifier=identifier, entity_type=entity_type)
        factory_business_mailing_address(business)

        # Create a filing and set it as the backfill cutoff
        filing_json = {"filing": {"header": {"name": "annualReport"}}}
        filing = factory_filing(business, filing_json)
        # Use a fixed date to create deterministic output
        filing.filing_date = datetime(2020, 1, 15)
        filing.save()

        business.backfill_cutoff_filing_id = filing.id

        bd = BusinessDocument(business, document_name)
        template_data = bd._get_template_data()  # pylint: disable=protected-access

        assert template_data.get('warning_text')
        assert 'Warning, data older than' in template_data['warning_text']
        assert 'January 15, 2020' in template_data['warning_text']
        assert 'may not appear in the Business Summary' in template_data['warning_text']

