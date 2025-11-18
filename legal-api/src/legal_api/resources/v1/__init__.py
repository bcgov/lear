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
"""Exposes all of the resource endpoints mounted in Flask-Blueprint style.

Uses restx namespaces to mount individual api endpoints into the service.

All services have 2 defaults sets of endpoints:
 - ops
 - meta
That are used to expose operational health information about the service, and meta information.
"""
from flask import Blueprint
from flask_restx import Api

from .business import API as BUSINESS_API
from .document_signature import API as DOCUMENT_API
from .meta import API as META_API
from .namerequest import API as NAME_REQUEST_PROXY_API
from .nr_type_map import API as NR_TYPE_MAP_API
from .ops import API as OPS_API

__all__ = ("API_BLUEPRINT", "OPS_BLUEPRINT")

# This will add the Authorize button to the swagger docs
# TODO oauth2 & openid may not yet be supported by restx <- check on this
AUTHORIZATIONS = {
    "apikey": {
        "type": "apiKey",
        "in": "header",
        "name": "Authorization"
    }
}

OPS_BLUEPRINT = Blueprint("API_OPS", __name__, url_prefix="/ops")

API_OPS = Api(OPS_BLUEPRINT,
              title="Service OPS API",
              version="1.0",
              description="The Core API for the Legal Entities System",
              security=["apikey"],
              authorizations=AUTHORIZATIONS)

API_OPS.add_namespace(OPS_API, path="/")

API_BLUEPRINT = Blueprint("API_V1", __name__, url_prefix="/api/v1")

API = Api(API_BLUEPRINT,
          title="BCROS Business API",
          version="1.0",
          description="The Core API for the Legal Entities System",
          security=["apikey"],
          authorizations=AUTHORIZATIONS)

API.add_namespace(META_API, path="/meta")
API.add_namespace(BUSINESS_API, path="/businesses")
API.add_namespace(DOCUMENT_API, path="/documents")
API.add_namespace(NAME_REQUEST_PROXY_API, path="/nameRequests")
API.add_namespace(NR_TYPE_MAP_API, path="/nrTypeMap")
