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
"""The Test Suites to ensure that the worker is operating correctly."""
import copy
import random

import pytest
from legal_api.models import Business, Filing, PartyRole
from legal_api.services import RegistrationBootstrapService
from registry_schemas.example_data import INCORPORATION_FILING_TEMPLATE

from entity_filer.worker import process_filing
from tests.pytest_marks import colin_api_integration, integration_affiliation
from tests.unit import create_filing


@pytest.fixture(scope='function')
def ia_filing(account):
    """Create a IA filing for processing."""
    from legal_api.services.bootstrap import AccountService

    filing = copy.deepcopy(INCORPORATION_FILING_TEMPLATE)
    payment_id = str(random.SystemRandom().getrandbits(0x58))
    bootstrap = RegistrationBootstrapService.create_bootstrap(account=account)
    RegistrationBootstrapService.register_bootstrap(bootstrap, bootstrap.identifier)
    identifier = bootstrap.identifier
    filing_id = (create_filing(payment_id, filing, bootstrap_id=bootstrap.identifier)).id

    yield filing_id

    try:
        rv = AccountService.delete_affiliation(account, identifier)
        print(rv)
    except Exception as err:
        print(err)


@colin_api_integration
@integration_affiliation
def test_incorporation_filing(app, session, ia_filing):
    """Assert we can retrieve a new corp number from COLIN and incorporate a business."""
    filing_msg = {'filing': {'id': ia_filing}}

    # Test
    process_filing(filing_msg, app)

    # Check outcome
    filing = Filing.find_by_id(ia_filing)
    business = Business.find_by_internal_id(filing.business_id)

    filing_json = filing.filing_json
    assert business
    assert filing
    assert filing.status == Filing.Status.COMPLETED.value
    assert business.identifier == filing_json['filing']['business']['identifier']
    assert business.founding_date.isoformat() == filing_json['filing']['business']['foundingDate']
    assert len(business.share_classes.all()) == len(filing_json['filing']['incorporationApplication']['shareClasses'])
    assert len(business.offices.all()) == len(filing_json['filing']['incorporationApplication']['offices'])

    assert len(PartyRole.get_parties_by_role(business.id, 'director')) == 1
    assert len(PartyRole.get_parties_by_role(business.id, 'incorporator')) == 1
    assert len(PartyRole.get_parties_by_role(business.id, 'completing_party')) == 1
    incorporator = (PartyRole.get_parties_by_role(business.id, 'incorporator'))[0]
    completing_party = (PartyRole.get_parties_by_role(business.id, 'completing_party'))[0]
    assert incorporator.appointment_date
    assert completing_party.appointment_date


def test_update_affiliation_error(mocker):
    """Assert that a message is posted to sentry if an error occurs."""
    import sentry_sdk
    from entity_filer.filing_processors import incorporation_filing
    filing = Filing(id=1)
    mocker.patch('sentry_sdk.capture_message')
    incorporation_filing.update_affiliation(None, filing)

    sentry_sdk.capture_message.assert_called_once_with(
        f'Queue Error: Affiliation error for filing:{filing.id}', level='error'
    )
