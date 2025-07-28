# Copyright © 2025 Province of British Columbia
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
"""Digital Credentials module.

Provides the service that handles DBC credential tasks for events.
"""
from flask import Flask

from .business_digital_credentials import bp as business_digital_credentials_endpoint
from .ops import bp as ops_endpoint


def register_endpoints(app: Flask):
    """Register endpoints with the flask application"""
    # Allow base route to match with, and without a trailing slash
    app.url_map.strict_slashes = False

    app.register_blueprint(
        url_prefix="/",
        blueprint=business_digital_credentials_endpoint,
    )

    app.register_blueprint(
        url_prefix="/ops",
        blueprint=ops_endpoint,
    )
