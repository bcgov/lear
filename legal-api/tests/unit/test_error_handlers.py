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
"""Test suite to assure the error handlers.

Test-Suite to ensure that the error handlers are working as expected.
"""
# import logging

from werkzeug.exceptions import HTTPException
from werkzeug.routing import RoutingException

from legal_api import errorhandlers


def test_handle_http_error_pass_through_routing_exception():  # pylint: disable=invalid-name
    """Assert that the RoutingException is passed through the handler."""
    response = errorhandlers.handle_http_error(RoutingException())

    assert isinstance(response, RoutingException)


def test_handle_http_error_pass(app):
    """Assert that the RoutingException is passed through the handler."""
    with app.test_request_context():
        err = HTTPException(description='description')
        err.code = 200
        response = errorhandlers.handle_http_error(err)

        assert response.status_code == 200


def test_handle_uncaught_error(app, caplog):
    """Handle any uncaught exceptions.

    Should return a response object with a 500 status_code
    and log an ERROR of an uncaught exception.
    Unhandled exceptions should get ticketed and managed.
    """
    with app.test_request_context():
        # logger = errorhandlers.logger
        caplog.set_level(errorhandlers.logging.ERROR, logger=errorhandlers.logger.name)
        resp = errorhandlers.handle_uncaught_error(Exception())

        assert resp.status_code == 500
        # assert ['Uncaught exception'] == [rec.message for rec in caplog.records]
