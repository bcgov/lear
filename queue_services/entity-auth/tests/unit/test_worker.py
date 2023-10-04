# Copyright © 2023 Province of British Columbia
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
"""The Test Suites to ensure that the entity auth is operating correctly."""
from http import HTTPStatus
import uuid

import pytest
from business_model import LegalEntity

from tests.unit import create_data, get_json_message


@pytest.mark.parametrize(
    "filing_type,entity_type,identifier",
    [
        ("registration", "SP", "FM1234567"),
        ("registration", "GP", "FM1234567"),
        ("incorporationApplication", "BC", "BC1234567"),
    ],
)
def test_new_legal_entity(
    app, session, client, mocker, filing_type, entity_type, identifier
):
    """Test new legal entity."""

    filing, legal_entity = create_data(filing_type, entity_type, identifier)

    def create_affiliation_side_effect(
        account,
        business_registration,
        business_name,
        corp_type_code,
        pass_code,
        details,
    ):
        assert account == 1
        assert business_registration == legal_entity.identifier
        assert business_name == legal_entity.legal_name
        assert corp_type_code == legal_entity.entity_type
        if entity_type in ["SP", "GP"]:
            party = legal_entity.entity_roles.all()[0].related_entity
            if party.entity_type == "organization":
                expected_pass_code = party.legal_name
            else:
                expected_pass_code = party.last_name + ", " + party.first_name
                if hasattr(party, "middle_initial") and party.middle_initial:
                    expected_pass_code = expected_pass_code + " " + party.middle_initial

            assert pass_code == expected_pass_code
            assert details == {
                "bootstrapIdentifier": filing.temp_reg,
                "identifier": legal_entity.identifier,
                "nrNumber": filing.filing_json["filing"][filing_type]["nameRequest"][
                    "nrNumber"
                ],
            }

        return HTTPStatus.OK

    mocker.patch(
        "entity_auth.services.bootstrap.AccountService.create_affiliation",
        side_effect=create_affiliation_side_effect,
    )

    def update_entity_side_effect(
        business_registration,
        business_name,
        corp_type_code,
    ):
        assert business_registration == filing.temp_reg
        assert business_name == legal_entity.identifier
        assert corp_type_code == ("RTMP" if entity_type in ["SP", "GP"] else "TMP")

        return HTTPStatus.OK

    mocker.patch(
        "entity_auth.services.bootstrap.AccountService.update_entity",
        side_effect=update_entity_side_effect,
    )

    message_id = str(uuid.uuid4())
    json_data = get_json_message(
        filing.id, identifier, message_id, f"bc.registry.business.{filing_type}"
    )
    rv = client.post("/", json=json_data)
    assert rv.status_code == HTTPStatus.OK


@pytest.mark.parametrize(
    "filing_type,entity_type,identifier",
    [
        ("changeOfRegistration", "SP", "FM1234567"),
        ("alteration", "BC", "BC1234567"),
        ("correction", "BC", "BC1234567"),
        ("correction", "BEN", "BC1234567"),
        ("correction", "CC", "BC1234567"),
        ("correction", "ULC", "BC1234567"),
        ("correction", "CP", "CP1234567"),
        ("correction", "SP", "FM1234567"),
        ("correction", "GP", "FM1234567"),
        ("dissolution", "BC", "BC1234567"),
        ("putBackOn", "BC", "BC1234567"),
        ("restoration", "SP", "FM1234567"),
    ],
)
def test_update_entity(
    app, session, client, mocker, filing_type, entity_type, identifier
):
    """Test update entity."""

    filing, legal_entity = create_data(filing_type, entity_type, identifier)

    def update_entity_side_effect(
        business_registration,
        business_name,
        corp_type_code,
        state,
    ):
        assert business_registration == filing.temp_reg
        assert business_name == legal_entity.identifier
        assert corp_type_code == ("RTMP" if entity_type in ["SP", "GP"] else "TMP")
        if filing_type == "dissolution":
            assert state == LegalEntity.State.HISTORICAL.name
        elif filing.filing_type in ["putBackOn", "restoration"]:
            assert state == LegalEntity.State.ACTIVE.name
        else:
            assert state is None

        return HTTPStatus.OK

    mocker.patch(
        "entity_auth.services.bootstrap.AccountService.update_entity",
        side_effect=update_entity_side_effect,
    )

    message_id = str(uuid.uuid4())
    json_data = get_json_message(
        filing.id, identifier, message_id, f"bc.registry.business.{filing_type}"
    )
    rv = client.post("/", json=json_data)
    assert rv.status_code == HTTPStatus.OK
