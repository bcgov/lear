# Copyright (c) 2026, Province of British Columbia

# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions are met:

# 1. Redistributions of source code must retain the above copyright notice, this
#    list of conditions and the following disclaimer.

# 2. Redistributions in binary form must reproduce the above copyright notice,
#    this list of conditions and the following disclaimer in the documentation
#    and/or other materials provided with the distribution.

# 3. Neither the name of the copyright holder nor the names of its
#    contributors may be used to endorse or promote products derived from
#    this software without specific prior written permission.

# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS"
# AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE
# IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE ARE
# DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT HOLDER OR CONTRIBUTORS BE LIABLE
# FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL
# DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR
# SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER
# CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY,
# OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE
# OF THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.
"""Test Suite for the Reports package."""
from unittest.mock import MagicMock

from legal_api.reports import business_document
from legal_api.reports.business_document import Amalgamation, AmalgamatingBusiness, BusinessDocument, Filing, colin
from legal_api.services.authz import STAFF_ROLE
from tests.unit.services.utils import create_header

from tests.unit.models import factory_business, factory_business_mailing_address


def make_foreign_amalgamating_business(foreign_identifier, foreign_name='Foreign Corp',
                                        foreign_jurisdiction='US',
                                        foreign_jurisdiction_region='WA'):
    """Return a lightweight mock that behaves like an AmalgamatingBusiness with foreign_name set."""
    ab = MagicMock()
    ab.foreign_name = foreign_name
    ab.foreign_identifier = foreign_identifier
    ab.foreign_jurisdiction = foreign_jurisdiction
    ab.foreign_jurisdiction_region = foreign_jurisdiction_region
    return ab


def make_amalgamation_filing_mock():
    """Return a minimal Filing-like mock for an amalgamationApplication."""
    filing = MagicMock()
    filing.effective_date = MagicMock()
    # Make effective_date comparisons always False so we skip the COLIN/tombstone branch.
    filing.effective_date.__lt__ = lambda self, other: False
    filing.transaction_id = 999
    filing.business_id = 1
    return filing


def set_amalgamation_details(app, jwt, session, monkeypatch,
                                  amalgamating_businesses_list,
                                  colin_query_side_effect=None):
    """Wire up mocks and invoke _set_amalgamation_details; return the resulting business dict."""
    identifier = 'BC9900001'
    entity_type = 'BC'

    fake_filing = make_amalgamation_filing_mock()
    fake_amalgamation = MagicMock()
    fake_amalgamation.id = 42

    # Patch Filing.get_filings_by_types so it returns our fake amalgamationApplication filing.
    monkeypatch.setattr(
        business_document.Filing, 'get_filings_by_types',
        lambda business_id, types: [fake_filing] if 'amalgamationApplication' in types else []
    )
    # Patch Filing.get_conversion_filings_by_conv_types to always return empty.
    monkeypatch.setattr(
        Filing, 'get_conversion_filings_by_conv_types',
        lambda business_id, types: []
    )
    # Patch Amalgamation.get_revision to return our fake amalgamation.
    monkeypatch.setattr(Amalgamation, 'get_revision', lambda txn_id, biz_id: fake_amalgamation)
    # Patch AmalgamatingBusiness.get_revision to return the provided list.
    monkeypatch.setattr(AmalgamatingBusiness, 'get_revision',
                        lambda txn_id, amalgamation_id: amalgamating_businesses_list)

    # Optionally patch colin.query_business.
    if colin_query_side_effect is not None:
        monkeypatch.setattr(colin, 'query_business', colin_query_side_effect)

    request_ctx = app.test_request_context(headers=create_header(jwt, [STAFF_ROLE], identifier))
    with request_ctx:
        business = factory_business(identifier=identifier, entity_type=entity_type)
        factory_business_mailing_address(business)

        bd = BusinessDocument(business, 'summary')
        business_json = {'business': business.json()}
        # _set_amalgamation_details reads _epoch_filing_date and _tombstone_filing_date;
        # leave them as None (default after __init__) so we enter the normal branch.
        bd._set_amalgamation_details(business_json)  # pylint: disable=protected-access

    return business_json