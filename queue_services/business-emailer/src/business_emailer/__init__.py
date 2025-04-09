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
"""The Entity Email service.

This module is the service worker for sending emails about entity related events.
"""
import sentry_sdk
from business_model.models.db import db
from flask import Flask
from sentry_sdk.integrations.flask import FlaskIntegration

from structured_logging import StructuredLogging

from .config import Config, ProdConfig
from .resources import register_endpoints
from .services import flags, gcp_queue


def create_app(environment: Config = ProdConfig, **kwargs) -> Flask:
    """Return a configured Flask App using the Factory method."""
    app = Flask(__name__)
    app.logger = StructuredLogging(app).get_logger()
    app.config.from_object(environment)

    # Configure Sentry
    if dsn := app.config.get("SENTRY_DSN", None):
        sentry_sdk.init(
            dsn=dsn,
            integrations=[FlaskIntegration()],
            send_default_pii=False,
        )

    # Configure LaunchDarkly
    if app.config.get("LD_SDK_KEY", None):
        flags.init_app(app)

    db.init_app(app)
    register_endpoints(app)
    gcp_queue.init_app(app)

    return app
