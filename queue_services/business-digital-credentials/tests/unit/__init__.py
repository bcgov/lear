# Copyright © 2025 Province of British Columbia
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
"""The Unit Tests and the helper routines."""
import json
from random import randrange

from unittest.mock import Mock

from business_model.models import (
    Batch,
    Business,
    DCBusinessUser,
    DCConnection,
    DCCredential,
    DCDefinition,
    Filing,
    Furnishing,
    Party,
    PartyRole,
    User,
)
from registry_schemas.example_data import (
    ALTERATION,
    ANNUAL_REPORT,
    CHANGE_OF_DIRECTORS,
    CORP_CHANGE_OF_ADDRESS,
)

from tests.unit.helpers import generate_temp_filing
from tests import EPOCH_DATETIME


FILING_TYPE_MAPPER = {
    # annual report structure is different than other 2
    "annualReport": ANNUAL_REPORT["filing"]["annualReport"],
    "changeOfAddress": CORP_CHANGE_OF_ADDRESS,
    "changeOfDirectors": CHANGE_OF_DIRECTORS,
    "alteration": ALTERATION,
}

LEGAL_NAME = "test business"


def create_user(user_name='test_user', firstname=None, lastname=None):
    """Return a new user model."""
    user = User()
    user.username = user_name
    user.firstname = firstname or 'TestFirst'
    user.lastname = lastname or 'TestLast'
    user.save()
    return user


def create_business(identifier, legal_type=None, legal_name=None, parties=None):
    """Return a test business."""
    business = Business()
    business.identifier = identifier
    business.legal_type = legal_type
    business.legal_name = legal_name

    for party in parties or []:
        if business.legal_type == Business.LegalTypes.SOLE_PROP:
            proprietor_role = create_party_role(
                None, None, party, None, None, PartyRole.RoleTypes.PROPRIETOR
            )
            business.party_roles.append(proprietor_role)
        elif legal_type == Business.LegalTypes.PARTNERSHIP:
            partner_role = create_party_role(
                None, None, party, None, None, PartyRole.RoleTypes.PARTNER
            )
            business.party_roles.append(partner_role)

    business.save()
    return business


def create_filing(
    token=None,
    filing_json=None,
    business_id=None,
    filing_date=EPOCH_DATETIME,
    bootstrap_id: str = None,
    meta_data=None,
):
    """Return a test filing."""
    filing = Filing()
    if token:
        filing.payment_token = str(token)
    filing.filing_date = filing_date

    if filing_json:
        filing.filing_json = filing_json
    if meta_data:
        filing._meta_data = meta_data
    if business_id:
        filing.business_id = business_id
    if bootstrap_id:
        filing.temp_reg = bootstrap_id

    filing.save()
    return filing


class Obj:
    """Make a custom object hook used by dict_to_obj."""

    def __init__(self, dict1):
        """Create instance of obj."""
        self.__dict__.update(dict1)


def dict_to_obj(dict1):
    """Convert dict to an object."""
    return json.loads(json.dumps(dict1), object_hook=Obj)


def create_mock_message(message_payload: dict):
    """Return a mock message that can be processed by the queue listener."""
    mock_msg = Mock()
    mock_msg.sequence = randrange(1000)
    mock_msg.data = dict_to_obj(message_payload)
    json_msg_payload = json.dumps(message_payload)
    mock_msg.data.decode = Mock(return_value=json_msg_payload)
    return mock_msg


def create_batch():
    """Return a test batch."""
    batch = Batch()
    batch.batch_type = Batch.BatchType.INVOLUNTARY_DISSOLUTION
    batch.status = Batch.BatchStatus.PROCESSING
    batch.save()
    return batch


def create_furnishing(
    session,
    business=None,
    batch_id=None,
    email="test@test.com",
    furnishing_name="DISSOLUTION_COMMENCEMENT_NO_AR",
):
    """Return a test furnishing."""
    furnishing = Furnishing()
    furnishing.furnishing_type = "EMAIL"
    furnishing.furnishing_name = furnishing_name
    furnishing.status = Furnishing.FurnishingStatus.QUEUED
    furnishing.email = email
    if business:
        furnishing.business_id = business.id
        furnishing.business_identifier = business.identifier
    else:
        business = create_business(
            identifier="BC123232", legal_type="BC", legal_name="Test Business"
        )
        furnishing.business_id = business.id
        furnishing.business_identifier = business.identifier
    if not batch_id:
        batch = create_batch()
        furnishing.batch_id = batch.id
    else:
        furnishing.batch_id = batch_id
    furnishing.save()
    return furnishing


def create_party_role(
    delivery_address,
    mailing_address,
    officer,
    appointment_date,
    cessation_date,
    role_type,
):
    """Create a role."""
    party = Party(
        first_name=officer["firstName"],
        last_name=officer["lastName"],
        middle_initial=officer["middleInitial"],
        party_type=officer["partyType"],
        organization_name=officer["organizationName"],
    )
    party.delivery_address = delivery_address
    party.mailing_address = mailing_address
    party.save()
    party_role = PartyRole(
        role=role_type.value,
        appointment_date=appointment_date,
        cessation_date=cessation_date,
        party_id=party.id,
    )
    return party_role


def create_dc_business_user(business, user) -> DCBusinessUser:
    """Create new dc_business_user object."""
    business_user = DCBusinessUser(business_id=business.id, user_id=user.id)
    business_user.save()
    return business_user


def create_dc_definition():
    """Create new dc_definition object."""
    definition = DCDefinition(
        credential_type=DCDefinition.CredentialType.business.name,
        schema_name="test_business_schema",
        schema_version="1.0.0",
        schema_id="test_schema_id",
        credential_definition_id="test_credential_definition_id",
    )
    definition.save()
    return definition


def create_dc_connection(
    business_user: DCBusinessUser, is_active=False
) -> DCConnection:
    """Create new dc_connection object."""
    connection = DCConnection(
        connection_id="0d94e18b-3a52-4122-8adf-33e2ccff681f",
        invitation_url="""http://192.168.65.3:8020?c_i=eyJAdHlwZSI6ICJodHRwczovL2RpZGNvbW0ub3JnL2Nvbm5lY3Rpb
25zLzEuMC9pbnZpdGF0aW9uIiwgIkBpZCI6ICIyZjU1M2JkZS01YWJlLTRkZDctODIwZi1mNWQ2Mjc1OWQxODgi
LCAicmVjaXBpZW50S2V5cyI6IFsiMkFHSjVrRDlVYU45OVpSeUFHZVZKNDkxclZhNzZwZGZYdkxXZkFyc2lKWjY
iXSwgImxhYmVsIjogImZhYmVyLmFnZW50IiwgInNlcnZpY2VFbmRwb2ludCI6ICJodHRwOi8vMTkyLjE2OC42NS4zOjgwMjAifQ==""",
        is_active=is_active,
        connection_state=(
            DCConnection.State.ACTIVE.value
            if is_active
            else DCConnection.State.INVITATION_SENT.value
        ),
        business_user_id=business_user.id,
        # Kept for legacy reasons, remove when possible
        business_id=business_user.business_id,
    )
    connection.save()
    return connection


def create_dc_credential(
    business_user=None,
    credential_exchange_id="test_credential_exchange_id",
    credential_revocation_id="123",
    revocation_registry_id="123",
    is_issued=True,
    is_revoked=False,
) -> DCCredential:
    """Create new dc_credential object."""
    if not business_user:
        identifier = "FM1234567"
        business_user = create_dc_business_user(
            create_business(identifier), create_user()
        )
    definition = create_dc_definition()
    connection = create_dc_connection(business_user, is_active=True)
    issued_credential = DCCredential(
        definition_id=definition.id,
        connection_id=connection.id,
        credential_exchange_id=credential_exchange_id,
        credential_revocation_id=credential_revocation_id,
        revocation_registry_id=revocation_registry_id,
        is_issued=is_issued,
        is_revoked=is_revoked,
    )
    issued_credential.save()
    return issued_credential
