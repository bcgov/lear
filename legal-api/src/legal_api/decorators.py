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
"""This module holds function decorators."""

from functools import wraps
from http import HTTPStatus

from flask import jsonify

from business_model.models import Business
from legal_api.services.authz import are_digital_credentials_allowed
from legal_api.utils.auth import jwt


def can_access_digital_credentials(f):
    """Ensure the business has access to digital credentials."""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        identifier = kwargs.get("identifier")

        if not (business := Business.find_by_identifier(identifier)):
            return jsonify({"message": f"{identifier} not found."}), HTTPStatus.NOT_FOUND

        if not are_digital_credentials_allowed(business, jwt):
            return jsonify({"message": f"digital credential not available for: {identifier}."}), HTTPStatus.UNAUTHORIZED

        return f(*args, **kwargs)
    return decorated_function
