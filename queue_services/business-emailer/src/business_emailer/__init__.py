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
from flask import Flask

from business_model.models.db import db
from structured_logging import StructuredLogging

from .config import Config, ProdConfig
from .resources import register_endpoints
from .services import flags, gcp_queue


def create_app(environment: Config = ProdConfig, **kwargs) -> Flask:
    """Return a configured Flask App using the Factory method."""
    app = Flask(__name__)
    app.logger = StructuredLogging(app).get_logger()
    app.config.from_object(environment)

    # Configure LaunchDarkly
    if app.config.get("LD_SDK_KEY", None):
        flags.init_app(app)

    if app.config.get("CLOUDSQL_INSTANCE_CONNECTION_NAME"):  # pragma: no cover
        from cloud_sql_connector import DBConfig
        db_config = DBConfig(
            instance_name=app.config["CLOUDSQL_INSTANCE_CONNECTION_NAME"],
            database=app.config.get("DB_NAME", ""),
            user=app.config.get("DB_USER", ""),
            ip_type=app.config["DB_IP_TYPE"],
            pool_recycle=60,
            schema="public",
        )
        app.config["SQLALCHEMY_ENGINE_OPTIONS"] = db_config.get_engine_options()

    db.init_app(app)
    register_endpoints(app)
    gcp_queue.init_app(app)

    return app
