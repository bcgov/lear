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

from .admin import bp_admin as admin_bp
from .business import bp as businesses_bp
from .business.business_digital_credentials import bp_dc as digital_credentials_bp
from .document import bp as document_bp
from .internal_services import bp as internal_bp
from .meta import bp as meta_bp
from .mras import bp as mras_bp
from .naics import bp as naics_bp
from .namerequest import bp as namerequest_bp
from .request_tracker import bp as request_tracker_bp


class V2Endpoint:
    """Setup all the V2 Endpoints."""

    def __init__(self):
        """Create the endpoint setup, without initializations."""
        self.app: Optional[Flask] = None

    def init_app(self, app):
        """Register and initialize the Endpoint setup."""
        if not app:
            raise Exception('Cannot initialize without a Flask App.')  # pylint: disable=broad-exception-raised

        self.app = app

        self.app.register_blueprint(meta_bp)
        self.app.register_blueprint(admin_bp)
        self.app.register_blueprint(businesses_bp)
        self.app.register_blueprint(digital_credentials_bp)
        self.app.register_blueprint(document_bp)
        self.app.register_blueprint(namerequest_bp)
        self.app.register_blueprint(naics_bp)
        self.app.register_blueprint(request_tracker_bp)
        self.app.register_blueprint(internal_bp)
        self.app.register_blueprint(mras_bp)


v2_endpoint = V2Endpoint()
