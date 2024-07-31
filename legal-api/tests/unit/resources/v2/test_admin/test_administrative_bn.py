# Copyright © 2022 Province of British Columbia
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

"""Tests to assure the Administrative BN end-point.

Test-Suite to ensure that the /admin/bn endpoint is working as expected.
"""

from http import HTTPStatus
from unittest.mock import patch

from legal_api.models import Business, UserRoles
from legal_api.resources.v2.admin import administrative_bn

from tests.unit.models import factory_business
from tests.unit.services.utils import create_header


def test_create_bn_request(session, client, jwt):
    """Create a new BN request."""
    identifier = 'FM0000001'
    factory_business(identifier, entity_type=Business.LegalTypes.SOLE_PROP.value)

    with patch.object(administrative_bn, 'publish_entity_event'):
        rv = client.post(f'/api/v2/admin/bn/{identifier}',
                         headers=create_header(jwt, [UserRoles.bn_edit], identifier))

        assert rv.status_code == HTTPStatus.CREATED
