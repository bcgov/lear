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

"""Tests to assure the business-aliases end-point.

Test-Suite to ensure that the /businesses../aliases endpoint is working as expected.
"""
from http import HTTPStatus

from legal_api.services.authz import STAFF_ROLE
from tests.unit import nested_session
from tests.unit.models import AlternateName, factory_alternate_name, factory_legal_entity
from tests.unit.services.utils import create_header


def test_get_business_aliases(session, client, jwt):
    """Assert that business aliases are returned."""
    # setup
    with nested_session(session):
        identifier = "CP7654321"
        legal_entity = factory_legal_entity(identifier)
        alias1 = factory_alternate_name(
            name="ABC Ltd.",
            name_type=AlternateName.NameType.TRANSLATION,
            legal_entity_id=legal_entity.id,
        )
        alias2 = factory_alternate_name(
            name="DEF Ltd.",
            name_type=AlternateName.NameType.TRANSLATION,
            legal_entity_id=legal_entity.id,
        )

        # test
        rv = client.get(
            f"/api/v2/businesses/{identifier}/aliases", headers=create_header(jwt, [STAFF_ROLE], identifier)
        )
        # check
        assert rv.status_code == HTTPStatus.OK
        assert "aliases" in rv.json
        assert len(rv.json["aliases"]) == 2


def test_get_business_aliases_only_translation(session, client, jwt):
    """Assert that only name translation is returned."""
    # setup
    with nested_session(session):
        identifier = "CP7654321"
        legal_entity = factory_legal_entity(identifier)
        alias1 = factory_alternate_name(
            name="ABC Ltd.",
            name_type=AlternateName.NameType.TRANSLATION,
            legal_entity_id=legal_entity.id,
        )
        alias2 = factory_alternate_name(
            name="DEF Ltd.",
            name_type=AlternateName.NameType.DBA,
            legal_entity_id=legal_entity.id,
        )

        # test
        rv = client.get(
            f"/api/v2/businesses/{identifier}/aliases", headers=create_header(jwt, [STAFF_ROLE], identifier)
        )
        # check
        assert rv.status_code == HTTPStatus.OK
        assert len(rv.json["aliases"]) == 1
        assert rv.json["aliases"][0]["name"] == "ABC Ltd."


def test_get_business_no_aliases(session, client, jwt):
    """Assert that business aliases are not returned."""
    # setup
    with nested_session(session):
        identifier = "CP7654321"
        factory_legal_entity(identifier)

        # test
        rv = client.get(
            f"/api/v2/businesses/{identifier}/aliases", headers=create_header(jwt, [STAFF_ROLE], identifier)
        )
        # check
        assert rv.status_code == HTTPStatus.OK
        assert rv.json["aliases"] == []


def test_get_business_alias_by_id(session, client, jwt):
    """Assert that business alias is returned."""
    # setup
    with nested_session(session):
        identifier = "CP7654321"
        legal_entity = factory_legal_entity(identifier)
        alias1 = factory_alternate_name(
            name="ABC Ltd.",
            name_type=AlternateName.NameType.TRANSLATION,
            legal_entity_id=legal_entity.id,
        )
        alias2 = factory_alternate_name(
            name="DEF Ltd.",
            name_type=AlternateName.NameType.TRANSLATION,
            legal_entity_id=legal_entity.id,
        )

        # test
        rv = client.get(
            f"/api/v2/businesses/{identifier}/aliases/{alias1.id}", headers=create_header(jwt, [STAFF_ROLE], identifier)
        )
        # check
        assert rv.status_code == HTTPStatus.OK
        assert rv.json["alias"]["name"] == "ABC Ltd."


def test_get_business_alias_by_invalid_id(session, client, jwt):
    """Assert that business alias is not returned."""
    # setup
    with nested_session(session):
        identifier = "CP7654321"
        legal_entity = factory_legal_entity(identifier)
        alias_id = 5000
        legal_entity.save()

        # test
        rv = client.get(
            f"/api/v2/businesses/{identifier}/aliases/{alias_id}", headers=create_header(jwt, [STAFF_ROLE], identifier)
        )
        # check
        assert rv.status_code == HTTPStatus.NOT_FOUND
        assert rv.json == {"message": f"{identifier} alias not found"}


def test_get_business_alias_by_type(session, client, jwt):
    """Assert that business aliases matching the type are returned."""
    # setup
    with nested_session(session):
        identifier = "CP7654321"
        legal_entity = factory_legal_entity(identifier)
        alias1 = factory_alternate_name(
            name="ABC Ltd.",
            name_type=AlternateName.NameType.TRANSLATION,
            legal_entity_id=legal_entity.id,
        )
        alias2 = factory_alternate_name(
            name="DEF Ltd.",
            name_type=AlternateName.NameType.TRANSLATION,
            legal_entity_id=legal_entity.id,
        )

        # test
        rv = client.get(
            f"/api/v2/businesses/{identifier}/aliases?type=translation", headers=create_header(jwt, [STAFF_ROLE], identifier)
        )
        # check
        assert rv.status_code == HTTPStatus.OK
        assert "aliases" in rv.json
        assert len(rv.json["aliases"]) == 2


def test_get_business_alias_by_invalid_type(session, client, jwt):
    """Assert that business aliases are not returned."""
    # setup
    with nested_session(session):
        identifier = "CP7654321"
        legal_entity = factory_legal_entity(identifier)
        alias1 = factory_alternate_name(
            name="ABC Ltd.",
            name_type=AlternateName.NameType.TRANSLATION,
            legal_entity_id=legal_entity.id,
        )
        alias2 = factory_alternate_name(
            name="DEF Ltd.",
            name_type=AlternateName.NameType.TRANSLATION,
            legal_entity_id=legal_entity.id,
        )

        # test
        rv = client.get(
            f"/api/v2/businesses/{identifier}/aliases?type=invalid",
            headers=create_header(jwt, [STAFF_ROLE], identifier),
        )
        # check
        assert rv.status_code == HTTPStatus.OK
        assert "aliases" in rv.json
        assert rv.json["aliases"] == []
