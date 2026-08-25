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

"""The Unit Test for the API.

For our purposes this server and its Postgres Database are part of the Unit Test Suite.

Also holds the shared builders for COLIN model objects used by the mocked-Oracle test
suites (auth-info, snapshot) - the fixtures composing them live in conftest.py.
"""
from colin_api.models import Business, Office, Party, ShareObject
from colin_api.models.shares import Share, ShareClass
from colin_api.utils.auth import jwt as _jwt


# what Address.as_dict emits
RAW_ADDRESS = {
    'streetAddress': '123 FAKE ST',
    'streetAddressAdditional': '',
    'addressCity': 'VICTORIA',
    'addressRegion': 'BC',
    'addressCountry': 'CANADA',
    'postalCode': 'V8V 8V8',
    'deliveryInstructions': '',
    'addressId': 4444,
    'actions': []
}

# the LEAR shape of the same address
LEAR_ADDRESS = {
    'id': 4444,
    'streetAddress': '123 FAKE ST',
    'streetAddressAdditional': '',
    'addressCity': 'VICTORIA',
    'addressRegion': 'BC',
    'addressCountry': 'CA',
    'postalCode': 'V8V 8V8',
    'deliveryInstructions': ''
}


def bypass_auth(mocker, roles_valid=True):
    """Stub out token validation on the jwt manager.

    The attribute names differ between flask-jwt-oidc releases (and validate_roles has taken
    different arities), so patch whichever the installed version exposes. MagicMock accepts
    any signature, so this holds across versions.
    """
    for attr in ('_require_auth_validation', '_validate_token', 'validate_token'):
        if hasattr(_jwt, attr):
            mocker.patch.object(_jwt, attr, return_value=None)
    mocker.patch.object(_jwt, 'validate_roles', return_value=roles_valid)


def build_business(**overrides):
    """Return a Business object as find_by_identifier would build it."""
    business = Business()
    business.corp_num = '0870226'
    business.corp_name = 'COLIN TEST COMPANY LTD.'
    business.corp_type = 'BC'
    # CORP_OP_STATE.OP_STATE_TYP_CD - only ever ACT/HIS; drives the response's LEAR-style state
    business.corp_state_class = 'ACT'
    business.good_standing = True
    business.business_number = '791861078BC0001'
    # COLIN returns admin_freeze as a 'True'/'False' string
    business.admin_freeze = 'False'
    # convert_to_json_datetime emits a '-00:00' suffix
    business.founding_date = '2000-01-01T08:00:00-00:00'
    business.email = 'registered.office@test.com'
    for key, value in overrides.items():
        setattr(business, key, value)
    return business


def build_director():
    """Return a Party object as Party.get_current would build it."""
    party = Party()
    party.officer = {
        'firstName': 'JANE', 'lastName': 'DOE', 'middleInitial': '',
        'organizationName': '', 'partyType': 'person'
    }
    party.delivery_address = dict(RAW_ADDRESS)
    party.mailing_address = dict(RAW_ADDRESS)
    party.title = ''
    party.appointment_date = '2010-05-05'
    party.cessation_date = None
    party.start_event_id = 111
    party.end_event_id = ''
    party.corp_party_id = 999
    party.roles = [{'roleType': 'Director', 'appointmentDate': '2010-05-05', 'cessationDate': None}]
    return party


def build_office(office_type):
    """Return an Office object as Office.get_current would build it."""
    office = Office()
    office.office_type = office_type
    office.delivery_address = dict(RAW_ADDRESS)
    office.mailing_address = dict(RAW_ADDRESS)
    return office


def build_share_structure():
    """Return the current ShareObject as ShareObject.get_all would build it."""
    series = Share()
    series.share_id = 1
    series.share_name = 'SERIES 1'
    series.has_max_shares = 'Y'  # COLIN semantics: 'N' means has a maximum
    series.has_special_rights = 'N'
    series.max_number_shares = None

    share_class = ShareClass()
    share_class.share_id = 0
    share_class.share_name = 'CLASS A'
    share_class.currency_type = 'OTH'
    share_class.other_currency = 'BITCOIN'
    share_class.has_max_shares = 'N'
    share_class.has_par_value = 'Y'
    share_class.has_special_rights = 'Y'
    share_class.par_value_amt = 1.5
    share_class.max_number_shares = 10000
    share_class.series = [series]

    share_struct = ShareObject()
    share_struct.end_event_id = None
    share_struct.share_classes = [share_class]
    return share_struct
