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
"""Actions related to the name requests of a business."""
import json
from http import HTTPStatus

import requests
import sentry_sdk
from entity_queue_common.service_utils import QueueException, logger
from flask import current_app
from legal_api.models import Business, Filing, RegistrationBootstrap
from legal_api.services import AccountService, Flags
from legal_api.services.utils import get_str


def consume_nr(business: Business, filing: Filing, filing_type: str = None, flags: Flags = None):
    """Update the nr to a consumed state."""
    try:
        if flags.is_on('enable-sandbox'):
            return

        filing_type = filing_type if filing_type else filing.filing_type
        # skip this if none (nrNumber will not be available for numbered company)
        if nr_num := get_str(filing.filing_json, f'/filing/{filing_type}/nameRequest/nrNumber'):

            namex_svc_url = current_app.config.get('NAMEX_API')
            token = AccountService.get_bearer_token()
            if flags and (flag_on := flags.is_on('namex-nro-decommissioned')):
                logger.debug('namex-nro-decommissioned flag: %s', flag_on)
                data = json.dumps({'state': 'CONSUMED', 'corpNum': business.identifier})
            else:
                data = json.dumps({'consume': {'corpNum': business.identifier}})

            rv = requests.patch(
                url=''.join([namex_svc_url, nr_num]),
                headers={**AccountService.CONTENT_TYPE_JSON,
                         'Authorization': AccountService.BEARER + token},
                data=data,
                timeout=AccountService.timeout
            )
            if not rv.status_code == HTTPStatus.OK:
                raise QueueException

            # remove the NR from the account
            if filing.temp_reg and (bootstrap := RegistrationBootstrap.find_by_identifier(filing.temp_reg)):
                AccountService.delete_affiliation(bootstrap.account, nr_num)
    except KeyError:
        pass  # return
    except Exception:  # pylint: disable=broad-except; note out any exception, but don't fail the call
        sentry_sdk.capture_message(f'Queue Error: Consume NR error for filing:{filing.id}', level='error')


def set_legal_name(business: Business, name_request_info: dict):
    """Set the legal_name in the business object."""
    if legal_name := name_request_info.get('legalName', None):
        business.legal_name = legal_name
