# Copyright © 2021 Province of British Columbia
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
"""Exposes all of the resource endpoints mounted in Flask-Blueprints."""
from typing import Optional

from flask import Flask

from .business import bp as businesses_bp
from .meta import bp as meta_bp


class V2Endpoint:
    """Setup all the V2 Endpoints."""

    def __init__(self):
        """Create the endpoint setup, without initializations."""
        self.app: Optional[Flask] = None

    def init_app(self, app):
        """Register and initialize the Endpoint setup."""
        if not app:
            raise Exception('Cannot initialize without a Flask App.')

        self.app = app

        self.app.register_blueprint(meta_bp)
        self.app.register_blueprint(businesses_bp)


v2_endpoint = V2Endpoint()


# @bp.route('/')
# def index():
#     return {"message": "hello"}, 200

# @bp.route('/info')
# def info():
#     return {"meta": "info"}, 200

# OPS_BLUEPRINT = Blueprint('API_OPS', __name__, url_prefix='/ops')

# API_OPS = Api(OPS_BLUEPRINT,
#               title='Service OPS API',
#               version='1.0',
#               description='The Core API for the Legal Entities System',
#               security=['apikey'],
#               authorizations=AUTHORIZATIONS)

# API_OPS.add_namespace(OPS_API, path='/')

# API_BLUEPRINT = Blueprint('API', __name__, url_prefix='/api/v1')

# API = Api(API_BLUEPRINT,
#           title='BCROS Business API',
#           version='1.0',
#           description='The Core API for the Legal Entities System',
#           security=['apikey'],
#           authorizations=AUTHORIZATIONS)

# API.add_namespace(META_API, path='/meta')
# API.add_namespace(BUSINESS_API, path='/businesses')
# API.add_namespace(DOCUMENT_API, path='/documents')
# API.add_namespace(NAME_REQUEST_PROXY_API, path='/nameRequests')
# API.add_namespace(NR_TYPE_MAP_API, path='/nrTypeMap')


# API_BLUEPRINT_v2 = Blueprint('API2', __name__, url_prefix='/api/v2')

# API2 = Api(
#     API_BLUEPRINT_v2,
#     title='BCROS Business API',
#     version='1.0',
#     description='The Core API for the Legal Entities System',
#     security=['apikey'],
#     authorizations=AUTHORIZATIONS)

# API2.add_namespace(BUSINESS_API, path='/businesses')


# from flask_restx import Api

# from .business import API as BUSINESS_API
# from .document_signature import API as DOCUMENT_API
# from .meta import API as META_API
# from .namerequest import API as NAME_REQUEST_PROXY_API
# from .nr_type_map import API as NR_TYPE_MAP_API
# from .ops import API as OPS_API

# from .blueprints import businesses_bp
# from .blueprints import meta_bp


# bp = Blueprint('API2', __name__, url_prefix='/api/v2')

# bp.register_blueprint(meta_bp)
# bp.register_blueprint(business_bp)
# __all__ = ('API_BLUEPRINT') #, 'OPS_BLUEPRINT', 'API_BLUEPRINT_v2')
