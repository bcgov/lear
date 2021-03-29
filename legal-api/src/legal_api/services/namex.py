# Copyright © 2020 Province of British Columbia
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

"""This provides the service for namex-api calls."""
from datetime import datetime
from enum import Enum

import datedelta
import pytz
import requests
from flask import current_app

from ..models import Filing
from .utils import get_str


class NameXService():
    """Provides services to use the namex-api."""

    DATE_FORMAT = '%Y-%m-%dT%H:%M:%S%z'

    class State(Enum):
        """Name request states."""

        APPROVED = 'APPROVED'
        CANCELLED = 'CANCELLED'
        COMPLETED = 'COMPLETED'
        CONDITIONAL = 'CONDITIONAL'
        DRAFT = 'DRAFT'
        EXPIRED = 'EXPIRED'
        HISTORICAL = 'HISTORICAL'
        HOLD = 'HOLD'
        INPROGRESS = 'INPROGRESS'
        REJECTED = 'REJECTED'
        NRO_UPDATING = 'NRO_UPDATING'

    @staticmethod
    def query_nr_number(identifier: str):
        """Return a JSON object with name request information."""
        auth_url = current_app.config.get('NAMEX_AUTH_SVC_URL')
        username = current_app.config.get('NAMEX_SERVICE_CLIENT_USERNAME')
        secret = current_app.config.get('NAMEX_SERVICE_CLIENT_SECRET')
        namex_url = current_app.config.get('NAMEX_SVC_URL')

        # Get access token for namex-api in a different keycloak realm
        auth = requests.post(auth_url, auth=(username, secret), headers={
            'Content-Type': 'application/x-www-form-urlencoded'}, data={'grant_type': 'client_credentials'})

        # Return the auth response if an error occurs
        if auth.status_code != 200:
            return auth.json()

        token = dict(auth.json())['access_token']

        # Perform proxy call using the inputted identifier (e.g. NR 1234567)
        nr_response = requests.get(namex_url + 'requests/' + identifier, headers={
            'Content-Type': 'application/json',
            'Authorization': 'Bearer ' + token
        })

        return nr_response.json()

    @staticmethod
    def update_nr(nr_json):
        """Update name request with nr_json."""
        auth_url = current_app.config.get('NAMEX_AUTH_SVC_URL')
        username = current_app.config.get('NAMEX_SERVICE_CLIENT_USERNAME')
        secret = current_app.config.get('NAMEX_SERVICE_CLIENT_SECRET')
        namex_url = current_app.config.get('NAMEX_SVC_URL')

        # Get access token for namex-api in a different keycloak realm
        auth = requests.post(auth_url, auth=(username, secret), headers={
            'Content-Type': 'application/x-www-form-urlencoded'}, data={'grant_type': 'client_credentials'})

        # Return the auth response if an error occurs
        if auth.status_code != 200:
            return auth.json()

        token = dict(auth.json())['access_token']

        # Perform update proxy call using nr number (e.g. NR 1234567)
        nr_response = requests.put(namex_url + 'requests/' + nr_json['nrNum'], headers={
            'Content-Type': 'application/json',
            'Authorization': 'Bearer ' + token
        }, json=nr_json)

        return nr_response

    @staticmethod
    def update_nr_as_future_effective(nr_json, future_effective_date: datetime):
        """Set expiration date of a name request to the future effective date and update the name request."""
        # Convert to namex supported timezone
        future_effective_date = future_effective_date.astimezone(pytz.timezone('GMT'))

        # add expiration buffer as future-effective-filings processing may not be immediate
        future_effective_date += datedelta.datedelta(days=1)

        nr_json['expirationDate'] = future_effective_date.strftime(NameXService.DATE_FORMAT)
        update_nr_response = NameXService.update_nr(nr_json)

        return update_nr_response

    @staticmethod
    def validate_nr(nr_json):
        """Provide validation info based on a name request response payload."""
        # Initial validation result state
        is_consumable = False
        is_approved = False
        is_expired = False
        consent_required = None
        consent_received = None
        nr_state = nr_json['state']

        if nr_json['expirationDate']:
            expiration_date = datetime.strptime(nr_json['expirationDate'], NameXService.DATE_FORMAT)
            if expiration_date < datetime.today().replace(tzinfo=pytz.utc):
                is_expired = True

        # Not consumable and not approved
        if nr_state not in (NameXService.State.APPROVED.value, NameXService.State.CONDITIONAL.value):
            is_consumable = False
            is_approved = False

        # Is approved
        elif nr_state == NameXService.State.APPROVED.value:
            is_approved = True
            consumed = False
            # Approved, but check if it has been consumed
            for name in nr_json['names']:
                # Already consumed
                if name['consumptionDate']:
                    consumed = True
            if not consumed:
                is_consumable = True

        # Is conditionally approved
        elif nr_state == NameXService.State.CONDITIONAL.value:
            is_approved = True
            consent_required = True
            consent_received = False
            # Check if consent received
            if nr_json['consentFlag'] == 'R':
                consent_received = True
                is_consumable = True

        return {
            'is_consumable': is_consumable,
            'is_approved': is_approved,
            'is_expired': is_expired,
            'consent_required': consent_required,
            'consent_received': consent_received
        }

    @staticmethod
    def is_date_past_expiration(nr_json, date_time):
        """Return true if the inputted date time is passed the name request expiration."""
        expiration_date = datetime.strptime(nr_json['expirationDate'], NameXService.DATE_FORMAT)
        expiration_date = expiration_date.astimezone(pytz.timezone('GMT'))
        if expiration_date < date_time:
            return True
        return False

    @staticmethod
    def get_approved_name(nr_json) -> str:
        """Get an approved name from nr json, if any."""
        nr_name = None
        state_to_check = None
        nr_state = nr_json['state']

        if nr_state == NameXService.State.APPROVED.value:
            state_to_check = nr_state
        elif nr_state == NameXService.State.CONDITIONAL.value:
            state_to_check = nr_state
        else:  # When NR is not approved
            return None

        for name in nr_json['names']:
            if name['state'] == state_to_check:
                nr_name = name['name']
                break

        return nr_name

    @staticmethod
    def has_correction_changed_name(filing) -> bool:
        """Has correction changed the legal name."""
        corrected_filing = Filing.find_by_id(filing['filing']['correction']['correctedFilingId'])
        nr_path = '/filing/incorporationApplication/nameRequest/nrNumber'
        legal_name_path = '/filing/incorporationApplication/nameRequest/legalName'
        old_nr_number = get_str(corrected_filing.json, nr_path)
        new_nr_number = get_str(filing, nr_path)
        old_legal_name = get_str(corrected_filing.json, legal_name_path)
        new_legal_name = get_str(filing, legal_name_path)
        return old_nr_number != new_nr_number or old_legal_name != new_legal_name
