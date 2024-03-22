# Copyright © 2021 Province of British Columbia
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

"""Tests to assure the business-parties end-point.

Test-Suite to ensure that the /businesses../parties endpoint is working as expected.
"""
import datetime
from http import HTTPStatus

import pytest

from legal_api.services.authz import ACCOUNT_IDENTITY, PUBLIC_USER, STAFF_ROLE, SYSTEM_ROLE
from tests.unit import nested_session
from tests.unit.models import (
    Address,
    EntityRole,
    LegalEntity,
    factory_alternate_name,
    factory_legal_entity,
    factory_party_role,
)
from tests.unit.services.utils import create_header


@pytest.mark.parametrize(
    "test_name,role",
    [
        ("public-user", PUBLIC_USER),
        ("account-identity", ACCOUNT_IDENTITY),
        ("staff", STAFF_ROLE),
        ("system", SYSTEM_ROLE),
    ],
)
def test_get_business_parties_one_party_multiple_roles(app, session, client, jwt, requests_mock, test_name, role):
    """Assert that business parties are returned."""
    with nested_session(session):
        # setup
        identifier = "CP7654321"
        legal_entity = factory_legal_entity(identifier)
        officer = LegalEntity(
            entity_type=LegalEntity.EntityTypes.PERSON.value, first_name="Connor", last_name="Horton", middle_initial=""
        )
        officer.save()
        party_role_1 = EntityRole(
            role_type=EntityRole.RoleTypes.director,
            appointment_date=datetime.datetime(2017, 5, 17),
            cessation_date=None,
            related_entity_id=officer.id,
        )
        party_role_2 = EntityRole(
            role_type=EntityRole.RoleTypes.custodian,
            appointment_date=datetime.datetime(2017, 5, 17),
            cessation_date=None,
            related_entity_id=officer.id,
        )
        legal_entity.entity_roles.append(party_role_1)
        legal_entity.entity_roles.append(party_role_2)
        legal_entity.save()

        # mock response from auth to give view access (not needed if staff / system)
        requests_mock.get(
            f"{app.config.get('AUTH_SVC_URL')}/entities/{identifier}/authorizations", json={"roles": ["view"]}
        )

        # test
        rv = client.get(f"/api/v2/businesses/{identifier}/parties", headers=create_header(jwt, [role], identifier))
        # check
        assert rv.status_code == HTTPStatus.OK
        assert "parties" in rv.json
        assert len(rv.json["parties"]) == 1
        assert len(rv.json["parties"][0]["roles"]) == 2


def test_get_business_parties_multiple_parties(session, client, jwt):
    """Assert that business parties are returned."""
    with nested_session(session):
        # setup
        identifier = "CP7654321"
        legal_entity = factory_legal_entity(identifier)
        officer_1 = LegalEntity(
            entity_type=LegalEntity.EntityTypes.PERSON.value, first_name="Connor", last_name="Horton", middle_initial=""
        )
        party_role_1 = EntityRole(
            role_type=EntityRole.RoleTypes.director,
            appointment_date=datetime.datetime(2017, 5, 17),
            cessation_date=None,
            related_entity=officer_1,
        )
        officer_2 = LegalEntity(
            entity_type=LegalEntity.EntityTypes.PERSON.value, first_name="Abraham", last_name="Mason", middle_initial=""
        )

        party_role_2 = EntityRole(
            role_type=EntityRole.RoleTypes.custodian,
            appointment_date=datetime.datetime(2017, 5, 17),
            cessation_date=None,
            related_entity=officer_2,
        )
        legal_entity.entity_roles.append(party_role_1)
        legal_entity.entity_roles.append(party_role_2)
        legal_entity.save()

        # test
        rv = client.get(
            f"/api/v2/businesses/{identifier}/parties", headers=create_header(jwt, [STAFF_ROLE], identifier)
        )
        # check
        assert rv.status_code == HTTPStatus.OK
        assert "parties" in rv.json
        assert len(rv.json["parties"]) == 2
        assert len(rv.json["parties"][0]["roles"]) == 1
        assert len(rv.json["parties"][1]["roles"]) == 1


def test_get_business_parties_by_role(session, client, jwt):
    """Assert that business parties are returned."""
    with nested_session(session):
        # setup
        identifier = "CP7654321"
        legal_entity = factory_legal_entity(identifier)
        party_address = Address(city="Test Mailing City", address_type=Address.DELIVERY)
        officer_1 = {
            "firstName": "Michael",
            "lastName": "Crane",
            "middleInitial": "Joe",
            "partyType": "person",
            "organizationName": "",
        }
        party_role_1 = factory_party_role(
            party_address, None, officer_1, datetime.datetime(2017, 5, 17), None, EntityRole.RoleTypes.director
        )
        officer_2 = {
            "firstName": "Connor",
            "lastName": "Horton",
            "middleInitial": "",
            "partyType": "person",
            "organizationName": "",
        }
        party_role_2 = factory_party_role(
            party_address, None, officer_2, datetime.datetime(2017, 5, 17), None, EntityRole.RoleTypes.custodian
        )
        legal_entity.entity_roles.append(party_role_1)
        legal_entity.entity_roles.append(party_role_2)
        legal_entity.save()

        # test
        rv = client.get(
            f"/api/v2/businesses/{identifier}/parties?role=Custodian",
            headers=create_header(jwt, [STAFF_ROLE], identifier),
        )
        # check
        assert rv.status_code == HTTPStatus.OK
        assert "parties" in rv.json
        assert len(rv.json["parties"]) == 1


def test_get_business_parties_by_invalid_role(session, client, jwt):
    """Assert that business parties are returned."""
    with nested_session(session):
        # setup
        identifier = "CP7654321"
        legal_entity = factory_legal_entity(identifier)
        party_address = Address(city="Test Mailing City", address_type=Address.DELIVERY)
        officer = {
            "firstName": "Michael",
            "lastName": "Crane",
            "middleInitial": "Joe",
            "partyType": "person",
            "organizationName": "",
        }
        party_role_1 = factory_party_role(
            party_address, None, officer, datetime.datetime(2017, 5, 17), None, EntityRole.RoleTypes.director
        )
        legal_entity.entity_roles.append(party_role_1)
        legal_entity.save()

        # test
        rv = client.get(
            f"/api/v2/businesses/{identifier}/parties?role=test", headers=create_header(jwt, [STAFF_ROLE], identifier)
        )
        # check
        assert rv.status_code == HTTPStatus.OK
        assert rv.json["parties"] == []


def test_get_business_no_parties(session, client, jwt):
    """Assert that business parties are not returned."""
    with nested_session(session):
        # setup
        identifier = "CP7654321"
        factory_legal_entity(identifier)

        # test
        rv = client.get(
            f"/api/v2/businesses/{identifier}/parties", headers=create_header(jwt, [STAFF_ROLE], identifier)
        )
        # check
        assert rv.status_code == HTTPStatus.OK
        assert rv.json["parties"] == []


@pytest.mark.parametrize(
    "test_name,params,expected",
    [
        ("test_no_ceased_returned", "", 0),
        ("test_all_ceased_returned", "?all=true", 1),
    ],
)
def test_get_business_ceased_parties(session, client, jwt, test_name, params, expected):
    """Assert that ceased parties are only returned when the correct params are included."""
    with nested_session(session):
        # setup
        identifier = "CP7654321"
        legal_entity = factory_legal_entity(identifier)
        officer = {
            "firstName": "Michael",
            "lastName": "Crane",
            "middleInitial": "Joe",
            "partyType": "person",
            "organizationName": "",
        }
        party_role = factory_party_role(
            None,
            None,
            officer,
            datetime.datetime(2012, 5, 17),
            datetime.datetime(2013, 5, 17),
            EntityRole.RoleTypes.director,
        )
        legal_entity.entity_roles.append(party_role)
        legal_entity.save()

    # test
    rv = client.get(
        f"/api/v2/businesses/{identifier}/parties{params}", headers=create_header(jwt, [STAFF_ROLE], identifier)
    )
    # check
    assert rv.status_code == HTTPStatus.OK
    assert len(rv.json["parties"]) == expected
    if expected != 0:
        assert rv.json["parties"][0]["officer"]["firstName"] == officer["firstName"]


def test_get_business_party_by_id(session, client, jwt):
    """Assert that business party is returned."""
    with nested_session(session):
        # setup
        identifier = "CP7654321"
        legal_entity = factory_legal_entity(identifier)
        officer = LegalEntity(
            first_name="Connor", last_name="Horton", middle_initial="", entity_type=LegalEntity.EntityTypes.PERSON.value
        )
        officer.save()
        party_role = EntityRole(
            role_type=EntityRole.RoleTypes.director,
            appointment_date=datetime.datetime(2017, 5, 17),
            cessation_date=None,
            related_entity_id=officer.id,
        )
        legal_entity.entity_roles.append(party_role)
        legal_entity.save()
        # test
        rv = client.get(
            f"/api/v2/businesses/{identifier}/parties/{officer.id}",
            headers=create_header(jwt, [STAFF_ROLE], identifier),
        )
        # check
        assert rv.status_code == HTTPStatus.OK
        assert rv.json["party"] is not None
        assert len(rv.json["party"]["roles"]) == 1


def test_get_business_party_by_invalid_id(session, client, jwt):
    """Assert that business party is not returned."""
    with nested_session(session):
        # setup
        identifier = "CP7654321"
        legal_entity = factory_legal_entity(identifier)
        party_id = 5000
        legal_entity.save()

        # test
        rv = client.get(
            f"/api/v2/businesses/{identifier}/parties/{party_id}", headers=create_header(jwt, [STAFF_ROLE], identifier)
        )
        # check
        assert rv.status_code == HTTPStatus.NOT_FOUND
        assert rv.json == {"message": f"Party {party_id} not found"}


def test_get_parties_invalid_business(session, client, jwt):
    """Assert that business is not returned."""
    with nested_session(session):
        # setup
        identifier = "CP7654321"

        # test
        rv = client.get(
            f"/api/v2/businesses/{identifier}/parties", headers=create_header(jwt, [STAFF_ROLE], identifier)
        )
        # check
        assert rv.status_code == HTTPStatus.NOT_FOUND
        assert rv.json == {"message": f"{identifier} not found"}


def test_get_parties_unauthorized(app, session, client, jwt, requests_mock):
    """Assert that parties are not returned for an unauthorized user."""
    with nested_session(session):
        # setup
        identifier = "CP7654321"
        legal_entity = factory_legal_entity(identifier)
        legal_entity.save()

        requests_mock.get(f"{app.config.get('AUTH_SVC_URL')}/entities/{identifier}/authorizations", json={"roles": []})

        # test
        rv = client.get(
            f"/api/v2/businesses/{identifier}/parties", headers=create_header(jwt, [PUBLIC_USER], identifier)
        )
        # check
        assert rv.status_code == HTTPStatus.UNAUTHORIZED
        assert rv.json == {"message": f"You are not authorized to view parties for {identifier}."}


def test_get_business_parties_sp_proprietor(app, session, client, jwt):
    """Assert that SP proprietor is returned."""
    with nested_session(session):
        # setup
        owner_identifier = "CP7654321"
        identifier = "FM7654321"
        legal_entity = factory_legal_entity(owner_identifier)
        alternate_name = factory_alternate_name(
            identifier=identifier,
            name="TEST OPERATING NAME",
            start_date=datetime.datetime.utcnow(),
            legal_entity_id=legal_entity.id,
        )

        legal_entity.alternate_names.append(alternate_name)
        legal_entity.skip_party_listener = True
        legal_entity.save()

        # test
        rv = client.get(
            f"/api/v2/businesses/{identifier}/parties", headers=create_header(jwt, [STAFF_ROLE], identifier)
        )

        # check
        assert rv.status_code == HTTPStatus.OK
        assert "parties" in rv.json
        assert len(rv.json["parties"]) == 1
