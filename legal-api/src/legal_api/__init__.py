# Copyright © 2025 Province of British Columbia
#
# Licensed under the BSD 3 Clause License, (the "License");
# you may not use this file except in compliance with the License.
# The template for the license can be found here
#    https://opensource.org/license/bsd-3-clause/
#
# Redistribution and use in source and binary forms,
# with or without modification, are permitted provided that the
# following conditions are met:
#
# 1. Redistributions of source code must retain the above copyright notice,
#    this list of conditions and the following disclaimer.
#
# 2. Redistributions in binary form must reproduce the above copyright notice,
#    this list of conditions and the following disclaimer in the documentation
#    and/or other materials provided with the distribution.
#
# 3. Neither the name of the copyright holder nor the names of its contributors
#    may be used to endorse or promote products derived from this software
#    without specific prior written permission.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS “AS IS”
# AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO,
# THE IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE
# ARE DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT HOLDER OR CONTRIBUTORS BE
# LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR
# CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF
# SUBSTITUTE GOODS OR SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS
# INTERRUPTION) HOWEVER CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN
# CONTRACT, STRICT LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE)
# ARISING IN ANY WAY OUT OF THE USE OF THIS SOFTWARE, EVEN IF ADVISED OF THE
# POSSIBILITY OF SUCH DAMAGE.
"""The Legal API service.

This module is the API for the Legal Entity system.
"""
import os

from flask import Flask, Response, current_app, jsonify, request
from flask_migrate import Migrate

import business_model_migrations
from business_model import models
from business_model.models import db
from business_model.models.db import init_db
from cloud_sql_connector import setup_pg8000_close_event_listener
from legal_api.config import DevConfig, MigrationConfig, ProdConfig, TestConfig
from legal_api.resources import endpoints
from legal_api.schemas import rsbc_schemas
from legal_api.scripts.document_service_import import document_service_bp
from legal_api.services import digital_credentials, flags, gcp_queue
from legal_api.services.authz import cache
from legal_api.translations import babel
from legal_api.utils.auth import jwt
from legal_api.utils.run_version import get_run_version
from registry_schemas import __version__ as registry_schemas_version
from structured_logging import StructuredLogging

CONFIG_MAP = {
    "development": DevConfig,
    "testing": TestConfig,
    "migration": MigrationConfig,
    "production": ProdConfig,
    "default": ProdConfig
}


def create_app(environment: str = os.getenv("DEPLOYMENT_ENV", "production"), **kwargs) -> Flask:
    """Return a configured Flask App using the Factory method."""
    app = Flask(__name__)
    app.logger = StructuredLogging(app).get_logger()
    app.config.from_object(CONFIG_MAP.get(environment, CONFIG_MAP["default"]))

    init_db(app)

    with app.app_context():  # db require app context
        digital_credentials.init_app(app)
        if app.config.get("CLOUDSQL_INSTANCE_CONNECTION_NAME"):  # pragma: no cover
            setup_pg8000_close_event_listener(db.engine)

    if environment == "migration":
        migrations_path = business_model_migrations.__file__
        migrations_dir = os.path.dirname(migrations_path)
        Migrate(app, db, directory=migrations_dir)
    
    else:
        rsbc_schemas.init_app(app)
        flags.init_app(app, kwargs.get("ld_test_data"))
        gcp_queue.init_app(app)
        babel.init_app(app)
        endpoints.init_app(app)
        cache.init_app(app)
        setup_jwt_manager(app, jwt)
        app.register_blueprint(document_service_bp)
        with app.app_context():  # db require app context
            digital_credentials.init_app(app)
    
    @app.before_request
    def add_logger_context():
        current_app.logger.debug("path: %s, app_name: %s, account_id: %s",
                                 request.path,
                                 request.headers.get("app-name"),
                                 request.headers.get("account-id"))

    @app.after_request
    def add_version(response: Response):
        """Add the api and schema version to the response headers."""
        version = get_run_version()
        response.headers["API"] = f"legal_api/{version}"
        response.headers["SCHEMAS"] = f"registry_schemas/{registry_schemas_version}"
        return response

    register_shellcontext(app)

    return app


def setup_jwt_manager(app, jwt_manager):
    """Use flask app to configure the JWTManager to work for a particular Realm."""
    def get_roles(a_dict):
        return a_dict["realm_access"]["roles"]  # pragma: no cover
    app.config["JWT_ROLE_CALLBACK"] = get_roles

    def custom_auth_error_handler(ex):
        response = jsonify(ex.error)
        response.status_code = ex.status_code
        response.headers["Access-Control-Allow-Origin"] = "*"
        return response
    app.config["JWT_OIDC_AUTH_ERROR_HANDLER"] = custom_auth_error_handler

    jwt_manager.init_app(app)


def register_shellcontext(app):
    """Register shell context objects."""
    def shell_context():
        """Shell context objects."""
        return {
            "app": app,
            "jwt": jwt,
            "db": db,
            "models": models}  # pragma: no cover

    app.shell_context_processor(shell_context)
