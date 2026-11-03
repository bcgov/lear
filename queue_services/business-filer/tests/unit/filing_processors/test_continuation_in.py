# Copyright © 2026 Province of British Columbia
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
"""The Unit Tests for the Incorporation filing."""

import copy
from datetime import datetime, timezone, timezone

import pytest
from business_model.models import Business, Filing, PartyRole
from registry_schemas.example_data import CONTINUATION_IN_FILING_TEMPLATE, CONTINUATION_IN_RELATIONSHIPS

from business_filer.filing_meta import FilingMeta
from business_filer.filing_processors import continuation_in
from tests.unit import create_filing


CONTINUATION_IN_FILING_TEMPLATE = copy.deepcopy(CONTINUATION_IN_FILING_TEMPLATE)


@pytest.mark.parametrize('legal_type, filing, next_corp_num ', [
    ('C', copy.deepcopy(CONTINUATION_IN_FILING_TEMPLATE), 'C0001095')
])
def test_continuation_in_filing_process(app, session, requests_mock, legal_type, filing, next_corp_num):
    """Assert that the incorporation object is correctly populated to model objects."""
    # setup
    mock_bearer_token = requests_mock.post(f'{app.config["ACCOUNT_SVC_AUTH_URL"]}', json={'access_token': 'fake-token'})
    mock_get_next_corp_num = requests_mock.post(f'{app.config["COLIN_API"]}/businesses/BC', json={'corpNum': int(next_corp_num[1:])})

    create_filing('123', filing)

    effective_date = datetime.now(timezone.utc)
    filing_rec = Filing(effective_date=effective_date, filing_json=filing)
    filing_meta = FilingMeta(application_date=effective_date)

    # test
    business, filing_rec, filing_meta = continuation_in.process(None, filing, filing_rec, filing_meta)

    # Assertions
    assert business.identifier == next_corp_num
    assert business.founding_date == effective_date
    assert business.state == Business.State.ACTIVE
    assert mock_bearer_token.called
    assert mock_bearer_token.call_count == 1
    assert mock_get_next_corp_num.called
    assert mock_get_next_corp_num.call_count == 1


def _relationships_filing() -> dict:
    """Return the continuationIn filing template with the relationships-shaped example section."""
    filing = copy.deepcopy(CONTINUATION_IN_FILING_TEMPLATE)
    filing['filing']['continuationIn'] = copy.deepcopy(CONTINUATION_IN_RELATIONSHIPS)
    return filing


@pytest.mark.parametrize('test_name, filing, corp_num, party_key, expected_directors, expected_filing_roles', [
    ('PARTIES', copy.deepcopy(CONTINUATION_IN_FILING_TEMPLATE), 9901, 'parties', ['SWANSON'],
     ['completing_party', 'incorporator']),
    ('RELATIONSHIPS', _relationships_filing(), 9902, 'relationships', ['SWANSON', 'QUAGMIRE'],
     ['completing_party']),
])
def test_continuation_in_party_shapes(app, session, requests_mock, test_name, filing, corp_num, party_key,
                                      expected_directors, expected_filing_roles):
    """Assert both party shapes create the same party rows and the stored filing keeps its shape."""
    requests_mock.post(f'{app.config["ACCOUNT_SVC_AUTH_URL"]}', json={'access_token': 'fake-token'})
    # saved businesses outlive the test session, so each case needs an identifier no other test looks up
    requests_mock.post(f'{app.config["COLIN_API"]}/businesses/BC', json={'corpNum': corp_num})

    effective_date = datetime.now(timezone.utc)
    filing_rec = create_filing('123', filing)  # saved so the jurisdiction row can reference it
    filing_rec.effective_date = effective_date
    filing_meta = FilingMeta(application_date=effective_date)

    business, filing_rec, filing_meta = continuation_in.process(None, filing, filing_rec, filing_meta)
    business.save()

    directors = sorted(business.party_roles.all(), key=lambda role: role.party.last_name)
    assert [role.role for role in directors] == [PartyRole.RoleTypes.DIRECTOR.value] * len(expected_directors)
    assert sorted(role.party.last_name for role in directors) == sorted(expected_directors)
    assert all(role.appointment_date.date().isoformat() == '2018-01-01' for role in directors)
    assert all(role.cessation_date is None for role in directors)
    assert all(role.party.delivery_address and role.party.mailing_address for role in directors)

    joe = next(role.party for role in directors if role.party.last_name == 'SWANSON')
    assert joe.first_name == 'JOE'
    assert joe.middle_initial == 'P'
    assert joe.party_type == 'person'
    assert joe.email == 'joe@email.com'

    assert sorted(role.role for role in filing_rec.filing_party_roles) == sorted(expected_filing_roles)

    stored = filing_rec.filing_json['filing']['continuationIn']
    assert party_key in stored
    assert ('parties' in stored) == (party_key == 'parties')
