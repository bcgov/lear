# Copyright © 2024 Province of British Columbia
#
# Licensed under the BSD 3 Clause License, (the "License");
# you may not use this file except in compliance with the License.
# The template for the license can be found here
#    https://opensource.org/license/bsd-3-clause/
#
# Redistribution and use in source and binary forms,
# with or without modification, are permitted provided that the
# following conditions are met:
#
# 1. Redistributions of source code must retain the above copyright notice,
#    this list of conditions and the following disclaimer.
#
# 2. Redistributions in binary form must reproduce the above copyright notice,
#    this list of conditions and the following disclaimer in the documentation
#    and/or other materials provided with the distribution.
#
# 3. Neither the name of the copyright holder nor the names of its contributors
#    may be used to endorse or promote products derived from this software
#    without specific prior written permission.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS “AS IS”
# AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO,
# THE IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE
# ARE DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT HOLDER OR CONTRIBUTORS BE
# LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR
# CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF
# SUBSTITUTE GOODS OR SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS
# INTERRUPTION) HOWEVER CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN
# CONTRACT, STRICT LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE)
# ARISING IN ANY WAY OUT OF THE USE OF THIS SOFTWARE, EVEN IF ADVISED OF THE
# POSSIBILITY OF SUCH DAMAGE.
"""GCP Auth Services."""
from flask import current_app
from google.oauth2 import id_token
from google.auth.transport import requests


def verify_gcp_jwt(flask_request):
    """Verify the bearer token as sign by gcp oauth."""
    msg = ""
    try:
        bearer_token = flask_request.headers.get("Authorization")
        current_app.logger.debug('bearer_token %s', bearer_token)
        token = bearer_token.split(" ")[1]
        audience = current_app.config.get("SUB_AUDIENCE")
        current_app.logger.debug('audience %s', audience)
        claim = id_token.verify_oauth2_token(
            token, requests.Request(), audience=audience
        )
        sa_email = current_app.config.get("SUB_SERVICE_ACCOUNT")
        current_app.logger.debug('sa_email %s', sa_email)
        if not claim["email_verified"] or claim["email"] != sa_email:
            msg = f"Invalid service account or email not verified for email: {claim['email']}\n"
        current_app.logger.debug('claim %s', claim)

    except Exception as err:
        msg = f"Invalid token: {err}\n"
    finally:
        return msg
