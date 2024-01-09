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

"""Tests to assure the internal end-point is working as expected."""
from http import HTTPStatus
from unittest.mock import patch

import pytest

from legal_api.models import LegalEntity, UserRoles
from legal_api.resources.v2 import internal_services
from legal_api.resources.v2.internal_services import ListFilingResource
from tests.unit.models import factory_legal_entity
from tests.unit.services.utils import create_header


def test_update_bn_move(session, client, jwt):
    """Assert that the endpoint updates tax_id."""
    identifier = "FM0000001"
    legal_entity = factory_legal_entity(identifier, entity_type=LegalEntity.EntityTypes.SOLE_PROP.value)
    legal_entity.tax_id = "993775204BC0001"
    legal_entity.save()

    new_bn = "993777399BC0001"
    with patch.object(internal_services, "publish_event"):
        with patch.object(
            ListFilingResource, "create_invoice", return_value=({"isPaymentActionRequired": False}, HTTPStatus.CREATED)
        ):
            rv = client.post(
                "/api/v2/internal/bnmove",
                headers=create_header(jwt, [UserRoles.system], identifier),
                json={"oldBn": legal_entity.tax_id, "newBn": new_bn},
            )
            assert rv.status_code == HTTPStatus.OK
            assert LegalEntity.find_by_tax_id(new_bn)


@pytest.mark.parametrize(
    "data",
    [
        ({}),
        ({"oldBn": "993775204BC0001"}),
        ({"newBn": "993777399BC0001"}),
    ],
)
def test_update_bn_move_missing_data(session, client, jwt, data):
    """Assert that the endpoint validates missing data."""
    rv = client.post("/api/v2/internal/bnmove", headers=create_header(jwt, [UserRoles.system]), json=data)
    assert rv.status_code == HTTPStatus.BAD_REQUEST
