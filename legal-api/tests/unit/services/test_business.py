# Copyright © 2019 Province of British Columbia
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

"""Tests to assure the Business Service.

Test-Suite to ensure that the Business Service is working as expected.
"""
from datetime import datetime

from flask import current_app
import pytest

from legal_api import services, status as http_status


def test_business_identifier_valid():
    """Assert that the identifier is valid."""
    identifier = 'CP1234567'
    business = services.Business()
    business.identifier = identifier

    assert identifier == business.identifier


def test_business_identifier_invalid():
    """Assert that an invalid identifier throws a BusinessException."""
    from legal_api.exceptions import BusinessException
    identifier = 'invalid'
    business = services.Business()

    with pytest.raises(BusinessException) as excinfo:
        business.identifier = identifier

    assert excinfo.value.status_code == 406
    assert excinfo.value.error == 'invalid-identifier-format'


TEST_BUSINESS_IDENTIFIERS_DATA = [
    ('Valid-COOP', 'CP1234567', True),
    ('Invalid-COOP', 'CP123456', False),
    ('Invalid-COOP', '', False),
    ('Valid-XCOOP', 'XCP1234567', True),
    ('Valid-XCOOP', 'XCP123456', False),
    ('Invalid-COOP', 'CP0000000', False),
    ('Invalid-Business', 'BP1234567', False)
]


@pytest.mark.parametrize('test_name,identifier,expected', TEST_BUSINESS_IDENTIFIERS_DATA)
def test_validate_format(test_name, identifier, expected):  # pylint: disable=unused-argument
    """Assert that the Business.identifier is formated and working correctly.

    This is a parameterized test, test cases should be added to TEST_BUSINESS_IDENTIFIERS_DATA
    """
    assert services.Business.validate_identifier(identifier) == expected


def factory_business_model(legal_name,
                           identifier,
                           founding_date,
                           last_remote_ledger_timestamp,
                           last_ledger_timestamp,
                           fiscal_year_end_date=None,
                           tax_id=None,
                           dissolution_date=None):
    """Return a valid Business object stamped with the supplied designation."""
    from legal_api.models import Business as BusinessModel
    b = BusinessModel(legal_name=legal_name,
                      identifier=identifier,
                      founding_date=founding_date,
                      last_remote_ledger_timestamp=last_remote_ledger_timestamp,
                      last_ledger_timestamp=last_ledger_timestamp,
                      fiscal_year_end_date=fiscal_year_end_date,
                      dissolution_date=dissolution_date,
                      tax_id=tax_id
                      )
    b.save()
    return b


def test_as_dict():
    """Assert that the Business is rendered correctly as a dict."""
    epoch_date = datetime.utcfromtimestamp(0)

    business = services.Business()
    business.legal_name = 'legal_name'
    business.identifier = 'CP1234567'
    business.founding_date = epoch_date
    business.last_remote_ledger_timestamp = epoch_date

    assert business.asdict() == {'legal_name': 'legal_name',
                                 'identifier': 'CP1234567',
                                 'founding_date': epoch_date.isoformat(),
                                 'last_ledger_timestamp': epoch_date.isoformat(),
                                 }

    business.dissolution_date = epoch_date
    assert business.asdict() == {'legal_name': 'legal_name',
                                 'identifier': 'CP1234567',
                                 'founding_date': epoch_date.isoformat(),
                                 'last_ledger_timestamp': epoch_date.isoformat(),
                                 'dissolution_date': datetime.date(epoch_date).isoformat()}
    business.dissolution_date = None

    business.fiscal_year_end_date = epoch_date
    assert business.asdict() == {'legal_name': 'legal_name',
                                 'identifier': 'CP1234567',
                                 'founding_date': epoch_date.isoformat(),
                                 'last_ledger_timestamp': epoch_date.isoformat(),
                                 'fiscal_year_end_date': datetime.date(epoch_date).isoformat()}
    business.fiscal_year_end_date = None

    business.tax_id = '12345'
    assert business.asdict() == {'legal_name': 'legal_name',
                                 'identifier': 'CP1234567',
                                 'founding_date': epoch_date.isoformat(),
                                 'last_ledger_timestamp': epoch_date.isoformat(),
                                 'tax_id': '12345'}
    business.tax_id = None


def test_business_set_disolution_date(session):
    """Assert that the business is saved to the cache."""
    identifier = 'CP7654321'
    b = services.Business()
    b.identifier = identifier
    b.legal_name = 'legal name'
    b.founding_date = datetime.utcfromtimestamp(0)
    b.last_remote_ledger_timestamp = datetime.utcfromtimestamp(0)
    b.save()

    business, _ = services.Business.find_by_identifier(identifier)
    business.dissolution_date = datetime.utcfromtimestamp(0)
    business.save()

    assert business is not None


TEST_BUSINESS_CACHE_DATA = [
    ('Remote==Cache',  # test name
     'CP7654321',      # ID
     '2019-04-15T20:05:49.068272+00:00',  # remote ledger timestamp
     '2019-04-15T20:05:49.068272+00:00',  # cache ledger timestamp
     ),
    ('Remote > Cache',  # test name
     'CP7654321',       # ID
     '2018-08-15T20:05:49.068272+00:00',  # remote ledger timestamp
     '2018-08-15T20:05:49.068272+00:00',  # cache ledger timestamp
     ),
    ('Remote < Cache',  # test name
     'CP7654321',       # ID
     '2019-04-15T20:05:49.068272+00:00',  # remote ledger timestamp
     '2019-04-20T20:05:49.068272+00:00',  # cache ledger timestamp
     ),
]


@pytest.mark.parametrize('test_name,identifier,remote_ts, cache_ts', TEST_BUSINESS_CACHE_DATA)
def test_business_retrieved_from_cache(session, test_name, identifier, remote_ts, cache_ts):
    """Assert that the business is saved to the cache."""
    if identifier:
        factory_business_model(legal_name='legal_name',
                               identifier=identifier,
                               founding_date=datetime.utcfromtimestamp(0),
                               last_remote_ledger_timestamp=datetime.fromisoformat(remote_ts),
                               last_ledger_timestamp=datetime.fromisoformat(cache_ts),
                               )

    business, _ = services.Business.find_by_identifier(identifier)

    assert business.identifier == identifier


def test_business_retrieved_cache_miss(session):
    """Assert that the business is retrieved from colin."""
    identifier = 'CP7654321'
    business, _ = services.Business.find_by_identifier(identifier)

    assert business.identifier == identifier


def test_business_cache_hit_remote_unavailable(session, config):
    """Assert that a cached business is retrieved when colin is unavailable."""
    from importlib import reload

    identifier = 'CP7654321'
    epoch = datetime.utcfromtimestamp(0)
    factory_business_model(legal_name='legal_name',
                           identifier=identifier,
                           founding_date=epoch,
                           last_remote_ledger_timestamp=epoch,
                           last_ledger_timestamp=epoch,
                           )

    # setup, point to no end-point and reload colin
    orig_url = config.get('COLIN_URL')
    config.update(COLIN_URL='https://never.going.to.return')
    reload(services.colin)

    # do test
    business, status = services.Business.find_by_identifier(identifier)

    # tear down (replace settings)
    config.update(COLIN_URL=orig_url)
    reload(services.colin)

    # determine if test worked
    assert business.identifier == identifier
    assert business.last_remote_ledger_timestamp.replace(tzinfo=None) == epoch.replace(tzinfo=None)
    assert status == http_status.HTTP_203_NON_AUTHORITATIVE_INFORMATION


def test_business_find_by_legal_name_pass(session):
    """Assert that the business can be found by name."""
    identifier = 'CP1234567'
    legal_name = 'legal name'
    b = services.Business()
    b.identifier = identifier
    b.legal_name = legal_name
    b.founding_date = datetime.utcfromtimestamp(0)
    b.save()

    b = services.Business().find_by_legal_name(legal_name)
    assert b is not None


def test_business_find_by_legal_name_not_exist(session):
    """Assert that the business isn't found for a non-existent name."""
    identifier = 'CP1234567'
    legal_name = 'legal name'
    b = services.Business()
    b.identifier = identifier
    b.legal_name = legal_name
    b.founding_date = datetime.utcfromtimestamp(0)
    b.save()

    b = services.Business().find_by_legal_name('not found')
    assert b is None


def test_business_cant_find_disolved_business(session):
    """Assert that the business can not be found, once it is disolved."""
    identifier = 'CP1234567'
    b = services.Business()
    b.legal_name = 'legal name'
    b.founding_date = datetime.utcfromtimestamp(0)
    b.dissolution_date = datetime.utcfromtimestamp(0)
    b.identifier = identifier
    b.save()

    # business is disolved, it should not be found by name search
    b, _ = services.Business.find_by_identifier(identifier)
    assert b is None


def test_business_find_by_legal_name_missing(session):
    """Assert that the business can be found by name."""
    identifier = 'CP1234567'
    b = services.Business()
    b.legal_name = 'legal name'
    b.founding_date = datetime.utcfromtimestamp(0)
    b.dissolution_date = None
    b.identifier = identifier
    b.tax_id = '123456789'
    b.fiscal_year_end_date = datetime(2001, 8, 5, 7, 7, 58, 272362)
    b.save()

    business, _ = services.Business.find_by_legal_name('')
    assert business is None


def test_business_find_by_identifier(session):
    """Assert that the business can be found by name."""
    identifier = 'CP7654321'
    b = services.Business()
    b.legal_name = 'legal name'
    b.founding_date = datetime.utcfromtimestamp(0)
    b.last_remote_ledger_timestamp = datetime.utcfromtimestamp(0)
    b.dissolution_date = None
    b.identifier = identifier
    b.tax_id = '123456789'
    b.fiscal_year_end_date = datetime(2001, 8, 5, 7, 7, 58, 272362)
    b.save()

    b, _ = services.Business.find_by_identifier(identifier)

    assert b is not None


def test_business_find_by_identifier_no_model_object(session):
    """Assert that the business can't be found with no model."""
    identifier = 'CP1234567'

    b, _ = services.Business.find_by_identifier(identifier)

    assert b is None


def test_business_find_by_identifier_missing_identifier(session):
    """Assert that the business can be found by name."""
    identifier = 'CP1234567'
    b = services.Business()
    b.legal_name = 'legal name'
    b.founding_date = datetime.utcfromtimestamp(0)
    b.dissolution_date = None
    b.identifier = identifier
    b.tax_id = '123456789'
    b.fiscal_year_end_date = datetime(2001, 8, 5, 7, 7, 58, 272362)
    b.save()

    b, _ = services.Business.find_by_identifier(None)

    assert b is None


def test_business_manage_last_update(session):
    """Assert that the last_update is set and managed correctly."""
    identifier = 'CP7654321'
    now = datetime.utcnow()

    business, _ = services.Business.find_by_identifier(identifier)
    business.last_ledger_timestamp = now
    business.save()
    business, _ = services.Business.find_by_identifier(identifier)

    assert business.last_ledger_timestamp.replace(tzinfo=None) == now.replace(tzinfo=None)
