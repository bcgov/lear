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

"""Tests to assure the RegistrationBootstrap Model.

Test-Suite to ensure that the RegistrationBootstrap Model is working as expected.
"""
import pytest
import sqlalchemy

from business_model.models import RegistrationBootstrap


def test_only_one_registration_bootstrap(session):
    """Assert that the identifier cannot be used more than once."""
    identifier = 'Tabc123'

    r = RegistrationBootstrap(identifier=identifier, account=12)
    r.save()

    with pytest.raises(sqlalchemy.exc.IntegrityError):
        p = RegistrationBootstrap(identifier=identifier, account=12)
        p.save()


def test_create_bootstrap_registrations(session):
    """Assert the service creates registrations."""
    identifier_base = 'Tabc123'

    for i in range(5):
        r = RegistrationBootstrap(identifier=identifier_base + str(i), account=12)
        r.save()
    assert r.identifier == identifier_base + str(4)
