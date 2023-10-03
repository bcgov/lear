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
"""Actions related to the name requests of a business."""
import json
from http import HTTPStatus

import requests
from flask import current_app, request
from business_model import Filing, LegalEntity, RegistrationBootstrap

from entity_auth.exceptions import NamexException
from entity_auth.services.logging import structured_log
from .bootstrap import AccountService


def consume_nr(legal_entity: LegalEntity, filing: Filing):
    """Update nr to consumed state."""
    try:
        # skip this if none (nrNumber will not be available for numbered company)
        if (
            nr_num := filing.filing_json.get("filing", {})
            .get(filing.filing_type, {})
            .get("nameRequest", {})
            .get("nrNumber")
        ):
            namex_svc_url = current_app.config.get("NAMEX_API")
            token = AccountService.get_bearer_token()

            # Create an entity record
            data = json.dumps({"consume": {"corpNum": legal_entity.identifier}})
            rv = requests.patch(
                url="".join([namex_svc_url, nr_num]),
                headers={
                    **AccountService.CONTENT_TYPE_JSON,
                    "Authorization": AccountService.BEARER + token,
                },
                data=data,
                timeout=AccountService.timeout,
            )
            if not rv.status_code == HTTPStatus.OK:
                raise NamexException

            # remove the NR from the account
            if filing.temp_reg and (
                bootstrap := RegistrationBootstrap.find_by_identifier(filing.temp_reg)
            ):
                AccountService.delete_affiliation(bootstrap.account, nr_num)
    except (
        Exception
    ):  # pylint: disable=broad-except; note out any exception, but don't fail the call
        structured_log(
            request,
            "ERROR",
            f"Queue Error: Consume NR error for filing:{filing.id}",
        )
