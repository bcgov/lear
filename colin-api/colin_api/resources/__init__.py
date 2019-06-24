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

Uses restplus namespaces to mount individual api endpoints into the service.

All services have 2 defaults sets of endpoints:
 - ops
 - meta
That are used to expose operational health information about the service, and meta information.
"""
from flask import Blueprint
from flask_restplus import Api

from .business import API as BUSINESS_API
from .directors import API as DIRECTORS_API
from .event import API as EVENT_API
from .filing import API as FILING_API
from .meta import API as META_API
from .office import API as OFFICE_API
from .ops import API as OPS_API


__all__ = ('API_BLUEPRINT', 'OPS_BLUEPRINT')

# This will add the Authorize button to the swagger docs
AUTHORIZATIONS = {
    'apikey': {
        'type': 'apiKey',
        'in': 'header',
        'name': 'Authorization'
    }
}

OPS_BLUEPRINT = Blueprint('API_OPS', __name__, url_prefix='/ops')

API_OPS = Api(OPS_BLUEPRINT,
              title='Service OPS API',
              version='1.0',
              description='The COLIN API for the Legal Entities System',
              security=['apikey'],
              authorizations=AUTHORIZATIONS)

API_OPS.add_namespace(OPS_API, path='/')

API_BLUEPRINT = Blueprint('API', __name__, url_prefix='/api/v1')

API = Api(API_BLUEPRINT,
          title='COLIN API',
          version='1.0',
          description='The COLIN API for the Legal Entities System',
          security=['apikey'],
          authorizations=AUTHORIZATIONS)

API.add_namespace(META_API, path='/meta')
API.add_namespace(BUSINESS_API, path='/businesses')
API.add_namespace(DIRECTORS_API, path='/businesses/directors')
API.add_namespace(EVENT_API, path='/businesses/event')
API.add_namespace(DIRECTORS_API, path='/businesses/office')
API.add_namespace(FILING_API, path='/businesses/filings')
