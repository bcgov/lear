# Copyright © 2019 Province of British Columbia
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
"""Validation for the Change of Name filing."""
from http import HTTPStatus
from typing import Final

from flask_babel import _ as babel

from legal_api.errors import Error
from legal_api.models import Business
from legal_api.services import flags, namex
from legal_api.services.utils import get_str


def validate(business: Business, filing: dict) -> Error:
    """Validate the Change of Name filing."""
    if not business or not filing:
        return Error(HTTPStatus.BAD_REQUEST, [{"error": babel("A valid business and filing are required.")}])
    msg = []
    legal_name_path = "/filing/changeOfName/legalName"
    legal_name = get_str(filing, legal_name_path)

    nr__number_path = "/filing/changeOfName/nameRequest/nrNumber"
    nr_number = get_str(filing, nr__number_path)

    if nr_number:
        # Skip the NR check in the Sandbox
        if flags.is_on("enable-sandbox"):
            return None
        # ensure NR is approved or conditionally approved
        nr_response = namex.query_nr_number(nr_number).json()
        validation_result = namex.validate_nr(nr_response)

        if not validation_result["is_consumable"]:
            msg.append({"error": babel("SR CON of Name Request is not approved."), "path": nr__number_path})

        # ensure NR request has the same legal name
        nr_legal_name_path: Final = "/filing/changeOfName/nameRequest/legalName"
        legal_name = get_str(filing, nr_legal_name_path)
        nr_name = namex.get_approved_name(nr_response)
        if nr_name != legal_name:
            msg.append({"error": babel("SR CON of Name Request has a different legal name."),
                        "path": legal_name_path})
    elif not legal_name:
        msg.append({"error": babel("Either Legal Name or NR number must be provided."),
                    "path": legal_name_path + " or " + nr__number_path})

    if msg:
        return Error(HTTPStatus.BAD_REQUEST, msg)
    return None
