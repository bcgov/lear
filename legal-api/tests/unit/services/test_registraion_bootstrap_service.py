# Copyright © 2020 Province of British Columbia
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

"""Tests to assure the RegistrationBootstrap Service.

Test-Suite to ensure that the RegistrationBootstrap Service is working as expected.
"""
import random
from http import HTTPStatus

from legal_api.services import RegistrationBootstrapService
from tests import integration_affiliation


def test_create_bootstrap_registrations(session):
    """Assert the service creates registrations."""
    r = RegistrationBootstrapService.create_bootstrap(account=28)
    assert r.identifier


@integration_affiliation
def test_create_account_affiliation(app_ctx):
    """Assert that the affiliation can be created."""
    from legal_api.services.bootstrap import AccountService
    _id = random.SystemRandom().getrandbits(0x58)
    r = AccountService.create_affiliation(account=28,
                                          business_registration=(f'XA{_id}')[:10],
                                          business_name='')

    assert r == HTTPStatus.OK


@integration_affiliation
def test_delete_account_affiliation(app_ctx):
    """Assert that it can be un-affiliated."""
    from legal_api.services.bootstrap import AccountService
    r = AccountService.delete_affiliation(account=28,
                                          business_registration='T231abc')

    # @TODO change this next sprint when affiliation service is updated.
    assert r == HTTPStatus.BAD_REQUEST
