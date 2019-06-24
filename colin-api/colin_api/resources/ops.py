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
"""Endpoints to check and manage the health of the service."""
import cx_Oracle
from flask import current_app
from flask_restplus import Namespace, Resource

from colin_api.resources.db import DB


API = Namespace('OPS', description='Service - OPS checks')


@API.route('healthz')
class Healthz(Resource):
    """Determines if the service and required dependnecies are still working.

    This could be thought of as a heartbeat for the service
    """

    @staticmethod
    def get():
        """Return a JSON object stating the health of the Service and dependencies."""
        try:
            # check db connection working
            cursor = DB.connection.cursor()
            cursor.execute('select 1 from dual')

        except cx_Oracle.DatabaseError as err:  # pylint:disable=c-extension-no-member
            try:
                return {'message': 'api is down', 'details': str(err)}, 500
            except Exception as err:  # pylint: disable=broad-except; want to catch any outstanding errors
                current_app.logger.error(err.with_traceback(None))
                return {'message': 'api is down'}, 500

        # made it here, so all checks passed
        return {'message': 'api is healthy'}, 200


@API.route('readyz')
class Readyz(Resource):
    """Determines if the service is ready to respond."""

    @staticmethod
    def get():
        """Return a JSON object that identifies if the service is setupAnd ready to work."""
        return {'message': 'api is ready'}, 200
