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
"""API endpoints for managing an Document Signature resource."""

from http import HTTPStatus

from flask_restx import Namespace, Resource, cors

from legal_api.services import MinioService
from legal_api.utils.auth import jwt
from legal_api.utils.util import cors_preflight


API = Namespace("documents", description="Endpoints for document signature management")


@cors_preflight("GET,OPTIONS")
@API.route("/<string:file_name>/signatures", methods=["GET", "OPTIONS"])
class DocumentSignature(Resource):
    """Resource for managing Document Signature."""

    @staticmethod
    @cors.crossdomain(origin="*")
    @jwt.requires_auth
    def get(file_name: str):
        """Return a pre-signed URL for the new document."""
        return MinioService.create_signed_put_url(file_name), HTTPStatus.OK
