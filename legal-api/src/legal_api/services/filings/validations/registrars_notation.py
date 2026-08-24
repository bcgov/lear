# Copyright © 2021 Province of British Columbia
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
"""Validation for the Registrars Notation filing."""
from http import HTTPStatus

from flask_babel import _ as babel

from business_model.models import Business
from legal_api.errors import Error


def validate(business: Business, registrars_notation: dict) -> Error | None:
    """Validate the Registrars Notation filing."""
    if not business or not registrars_notation:
        return Error(HTTPStatus.BAD_REQUEST, [{"error": babel("A valid business and filing are required.")}])
    msg = []

    data = registrars_notation["filing"]["registrarsNotation"]
    path = "/filing/registrarsNotation"
    if effect_of_order := data.get("effectOfOrder"):
        if effect_of_order == "planOfArrangement":
            if not data.get("fileNumber"):
                msg.append({"error": babel(
                    "Court Order Number is required when this filing is pursuant to a Plan of Arrangement."),
                    "path": f"{path}/fileNumber"})
        else:
            msg.append({"error": babel("Invalid effectOfOrder."), "path": f"{path}/effectOfOrder"})

    if msg:
        return Error(HTTPStatus.BAD_REQUEST, msg)
    return None
