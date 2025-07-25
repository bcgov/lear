# Copyright © 2022 Province of British Columbia
#
# Licensed under the Apache License, Version 2.0 (the 'License');
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an 'AS IS' BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
"""Test suite to ensure business document request is validated correctly."""
import datedelta
import pytest
from legal_api.services.business import validate_document_request
from legal_api.models import Business
from tests.unit.models import factory_business
from datetime import datetime, timezone


@pytest.mark.parametrize(
    'test_status, document_type, legal_type, identifier, expected_msg',
    [
        ('FAIL', 'cstat', 'SP', 'FM1234567', 'Specified document type is not valid for the entity.'),
        ('FAIL', 'cstat', 'GP', 'FM1234567', 'Specified document type is not valid for the entity.'),
        ('SUCCESS', 'cstat', 'BEN', 'BC1234567', None),
        ('HISTORICAL', 'cstat', 'BC', 'BC1234567',
         'Specified document type is not valid for the current entity status.'),
        ('HISTORICAL', 'cstat', 'ULC', 'BC1234567',
         'Specified document type is not valid for the current entity status.'),
        ('HISTORICAL', 'cstat', 'CC', 'BC1234567',
         'Specified document type is not valid for the current entity status.'),
        ('SUCCESS', 'cstat', 'CP', 'CP1234567', None),
        ('SUCCESS', 'cstat', 'BC', 'BC1234567', None),
        ('SUCCESS', 'cstat', 'ULC', 'BC1234567', None),
        ('SUCCESS', 'cstat', 'CC', 'BC1234567', None),
        ('SUCCESS', 'lseal', 'CP', 'CP1234567', None),
        ('SUCCESS', 'lseal', 'BC', 'BC1234567', None),
        ('SUCCESS', 'lseal', 'ULC', 'BC1234567', None),
        ('SUCCESS', 'lseal', 'CC', 'BC1234567', None),
        ('SUCCESS', 'lseal', 'SP', 'FM1234567', None),
        ('SUCCESS', 'lseal', 'GP', 'FM1234567', None),
        ('SUCCESS', 'cogs', 'CP', 'CP1234567', None),
        ('SUCCESS', 'cogs', 'BC', 'BC1234567', None),
        ('SUCCESS', 'cogs', 'ULC', 'BC1234567', None),
        ('SUCCESS', 'cogs', 'CC', 'BC1234567', None),
        ('FAIL', 'cogs', 'SP', 'FM1234567', 'Specified document type is not valid for the entity.'),
        ('FAIL', 'cogs', 'GP', 'FM1234567', 'Specified document type is not valid for the entity.'),
    ]
)
def test_document_legal_type(session, test_status, document_type, legal_type, identifier, expected_msg):
    """Assert valid document legal type."""
    business = factory_business(identifier,
                                founding_date=(datetime.now(timezone.utc) - datedelta.YEAR),
                                last_ar_date=datetime.now(timezone.utc),
                                entity_type=legal_type
                                )
    if test_status == 'HISTORICAL':
        business.dissolution_date = datetime.now(timezone.utc)
        business.state = Business.State.HISTORICAL
        business.save()
    err = validate_document_request(document_type, business)

    # validate outcomes
    if test_status in ['FAIL', 'HISTORICAL']:
        assert expected_msg == err.msg[0]['error']
    else:
        assert not err
