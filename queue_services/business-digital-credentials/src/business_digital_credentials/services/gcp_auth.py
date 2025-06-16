# Copyright © 2025 Province of British Columbia
#
# Licensed under the BSD 3 Clause License, (the "License");
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
"""GCP Auth Services."""
from flask import current_app
from google.auth.transport import requests
from google.oauth2 import id_token


def verify_gcp_jwt(flask_request):
    """Verify the bearer token as sign by gcp oauth."""
    msg = ""
    try:
        bearer_token = flask_request.headers.get("Authorization")
        current_app.logger.debug("bearer_token %s", bearer_token)
        token = bearer_token.split(" ")[1]
        audience = current_app.config.get("SUB_AUDIENCE")
        current_app.logger.debug("audience %s", audience)
        claim = id_token.verify_oauth2_token(
            token, requests.Request(), audience=audience
        )
        sa_email = current_app.config.get("SUB_SERVICE_ACCOUNT")
        current_app.logger.debug("sa_email %s", sa_email)
        if not claim["email_verified"] or claim["email"] != sa_email:
            msg = f"Invalid service account or email not verified for email: {claim['email']}\n"
        current_app.logger.debug("claim %s", claim)

    except Exception as err:
        msg = f"Invalid token: {err}\n"
    finally:
        return msg # we want to silence exception # noqa: B012
