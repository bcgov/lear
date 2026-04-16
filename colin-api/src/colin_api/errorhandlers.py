# Copyright © 2023 Province of British Columbia
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

"""Core error handlers and custom exceptions.

Following best practices from:
http://flask.pocoo.org/docs/1.0/errorhandling/
http://flask.pocoo.org/docs/1.0/patterns/apierrors/
"""

import logging
import re
import sys

from flask import jsonify, request
from flask_jwt_oidc import AuthError
from werkzeug.exceptions import HTTPException
from werkzeug.routing import RoutingException


logger = logging.getLogger(__name__)


def init_app(api):
    """Initialize the error handlers for the Flask app instance."""
    api.error_handlers[AuthError] = handle_auth_error
    api.error_handlers[HTTPException] = handle_http_error
    api.error_handlers[Exception] = handle_uncaught_error


def handle_auth_error(error):
    """Handle auth errors."""
    error_details = error.error
    return error_details, error.status_code


def handle_http_error(error):
    """Handle HTTPExceptions.

    Include the error description and corresponding status code, known to be
    available on the werkzeug HTTPExceptions.
    """
    # As werkzeug's routing exceptions also inherit from HTTPException,
    # check for those and allow them to return with redirect responses.
    if isinstance(error, RoutingException):
        return error

    app_name = request.headers.get('App-Name', 'unknown').strip()
    # Allow spaces as well as letters, numbers, underscores and hyphens
    if not re.match(r'^[a-zA-Z0-9 _-]+$', app_name):
        app_name = 'invalid app name'
    logger.error('HTTP error from app: %s', app_name, exc_info=sys.exc_info())

    error_details = error.response
    return {'message': error.description}, error_details.status_code


def handle_uncaught_error(error: Exception):  # pylint: disable=unused-argument
    """Handle any uncaught exceptions.

    Since the handler suppresses the actual exception, log it explicitly to
    ensure it's logged.
    """
    app_name = request.headers.get('App-Name', 'unknown').strip()
    # Allow spaces as well as letters, numbers, underscores and hyphens
    if not re.match(r'^[a-zA-Z0-9 _-]+$', app_name):
        app_name = 'invalid app name'
    logger.error('Uncaught exception from app: %s', app_name, exc_info=sys.exc_info())

    if isinstance(error, KeyError):
        return jsonify({'message': f'A required field {error.args[0]} was missing or invalid.'}), 400
    if isinstance(error, AttributeError):
        return jsonify(
            {'message': 'Invalid request format, one or more fields have an unexpected value or structure.'}
        ), 400
    if isinstance(error, TypeError):
        return jsonify({'message': f'Encountered an error processing the request, {str(error)}'}), 400

    response = jsonify({'message': 'Internal server error'})
    response.status_code = 500
    return response
