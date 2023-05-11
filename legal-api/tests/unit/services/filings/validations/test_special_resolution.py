# Copyright © 2019 Province of British Columbia
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
"""Test suite to ensure Special Resolution is validated correctly."""
import copy
from datetime import datetime
from http import HTTPStatus

import pytest
from registry_schemas.example_data import FILING_HEADER, SPECIAL_RESOLUTION

from legal_api.models import Business
from legal_api.services.filings.validations.special_resolution import validate
from . import create_utc_future_date_str


@pytest.mark.parametrize(
    'test_name, resolution, identifier, resolution_date, signing_date, signatory_given_name, signatory_family_name, business_founding_date, expected_code, expected_msg',
    [
        ('SUCCESS', 'some resolution', 'CP1234567', '2021-01-10', '2021-01-10', 'jane', 'doe', '2010-01-10', None, None),
        ('MISSING - resolution', None, 'CP1234567', '2021-01-10', '2021-01-10', 'jane', 'doe', '2010-01-10',
         HTTPStatus.BAD_REQUEST, 'Resolution must be provided.'),
        ('MISSING - resolution date', 'some resolution', 'CP1234567', None, '2021-01-10', 'jane', 'doe', '2010-01-10',
         HTTPStatus.BAD_REQUEST, 'Resolution date is required.'),
        ('INVALID - resolution > 2MB', 'x' * (2097152 + 1), 'CP1234567', '2009-01-10', '2021-01-10', 'jane',
         'doe', '2010-01-10', HTTPStatus.BAD_REQUEST, 'Resolution must be 2MB or less.'),
        ('INVALID - resolution date < incorp date', 'some resolution', 'CP1234567', '2009-01-10', '2021-01-10', 'jane',
         'doe', '2010-01-10', HTTPStatus.BAD_REQUEST, 'Resolution date cannot be earlier than the incorporation date.'),
        ('INVALID - resolution date is future date', 'some resolution', 'CP1234567',
         create_utc_future_date_str(days=10), '2021-01-10', 'jane', 'doe', '2010-01-10', HTTPStatus.BAD_REQUEST,
         'Resolution date cannot be in the future.'),
        ('MISSING - signing date', 'some resolution', 'CP1234567', '2021-01-10', None, 'jane', 'doe', '2010-01-10',
         HTTPStatus.BAD_REQUEST, 'Signing date is required.'),
        ('INVALID - signing date is future date', 'some resolution', 'CP1234567',
         '2010-01-10', create_utc_future_date_str(days=10), 'jane', 'doe', '2010-01-10', HTTPStatus.BAD_REQUEST,
         'Signing date cannot be in the future.'),
        ('INVALID - signing date before resolution date', 'some resolution', 'CP1234567', '2010-01-10', '2010-01-09',
         'jane', 'doe', '2010-01-10', HTTPStatus.BAD_REQUEST, 'Signing date cannot be before the resolution date.'),
        ('SUCCESS - signing & resolution date are same', 'some resolution', 'CP1234567', '2010-01-10', '2010-01-10',
         'jane', 'doe', '2010-01-10', None, None),
        ('SUCCESS - signing after resolution date', 'some resolution', 'CP1234567', '2010-01-10', '2010-01-11',
         'jane', 'doe', '2010-01-10', None, None),
        ('MISSING - signatory first name', 'some resolution', 'CP1234567', '2021-01-10', '2021-01-10', None, 'doe',
         '2010-01-10', HTTPStatus.BAD_REQUEST, 'Signatory given name is required.'),
        ('MISSING - signatory last name', 'some resolution', 'CP1234567', '2021-01-10', '2021-01-10', 'jane', None,
         '2010-01-10', HTTPStatus.BAD_REQUEST, 'Signatory family name is required.'),
    ], ids=lambda param: repr(param)[:75].replace("'", '')
)
def test_validate(session, test_name, resolution, identifier, resolution_date, signing_date, signatory_given_name,
                  signatory_family_name, business_founding_date, expected_code, expected_msg):
    """Assert that a SR can be validated."""
    # setup
    business = Business(identifier=identifier)
    business.founding_date = datetime.strptime(business_founding_date, '%Y-%m-%d')

    filing = copy.deepcopy(FILING_HEADER)
    filing['filing']['specialResolution'] = copy.deepcopy(SPECIAL_RESOLUTION)
    if resolution:
        filing['filing']['specialResolution']['resolution'] = resolution
    else:
        del filing['filing']['specialResolution']['resolution']

    if resolution_date:
        filing['filing']['specialResolution']['resolutionDate'] = resolution_date
    else:
        del filing['filing']['specialResolution']['resolutionDate']

    if signing_date:
        filing['filing']['specialResolution']['signingDate'] = signing_date
    else:
        del filing['filing']['specialResolution']['signingDate']

    if signatory_given_name:
        filing['filing']['specialResolution']['signatory']['givenName'] = signatory_given_name
    else:
        del filing['filing']['specialResolution']['signatory']['givenName']

    if signatory_family_name:
        filing['filing']['specialResolution']['signatory']['familyName'] = signatory_family_name
    else:
        del filing['filing']['specialResolution']['signatory']['familyName']

    # perform test
    err = validate(business, filing)

    # validate outcomes
    if expected_code or expected_msg:
        assert expected_code == err.code
        assert expected_msg == err.msg[0]['error']
    else:
        assert not err
