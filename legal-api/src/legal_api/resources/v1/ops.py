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

from flask_restx import Namespace, Resource
from sqlalchemy import exc, text

from legal_api.models import db


API = Namespace("OPS", description="Service - OPS checks")

SQL = text("select 1")


@API.route("healthz")
class Healthz(Resource):
    """Determines if the service and required dependencies are still working.

    This could be thought of as a heartbeat for the service
    """

    @staticmethod
    def get():
        """Return a JSON object stating the health of the Service and dependencies."""
        try:
            db.engine.execute(SQL)
        except exc.SQLAlchemyError:
            return {"message": "api is down"}, 500

        # made it here, so all checks passed
        return {"message": "api is healthy"}, 200


@API.route("readyz")
class Readyz(Resource):
    """Determines if the service is ready to respond."""

    @staticmethod
    def get():
        """Return a JSON object that identifies if the service is setupAnd ready to work."""
        # TODO: add a poll to the DB when called
        return {"message": "api is ready"}, 200
