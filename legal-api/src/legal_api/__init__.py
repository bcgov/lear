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

from flask import Flask, jsonify  # noqa: I001
from registry_schemas import __version__ as registry_schemas_version  # noqa: I005
from registry_schemas.flask import SchemaServices  # noqa: I001
from structured_logging import StructuredLogging

from legal_api import config, models
from legal_api.models import db
from legal_api.models.db import init_db
from legal_api.resources import endpoints
from legal_api.scripts.document_service_import import document_service_bp  # noqa: I001, E501; pylint: disable=ungrouped-imports; conflicts with Flake8; isort: skip
from legal_api.schemas import rsbc_schemas
from legal_api.services import digital_credentials, flags, gcp_queue, queue
from legal_api.services.authz import cache
from legal_api.translations import babel
from legal_api.utils.auth import jwt
from legal_api.utils.logging import setup_logging
from legal_api.utils.run_version import get_run_version

setup_logging(os.path.join(os.path.abspath(os.path.dirname(__file__)), 'logging.conf'))  # important to do this first


def create_app(run_mode=os.getenv('FLASK_ENV', 'production')):
    """Return a configured Flask App using the Factory method."""
    app = Flask(__name__)
    app.register_blueprint(document_service_bp)
    app.config.from_object(config.CONFIGURATION[run_mode])

    app.logger = StructuredLogging(app).get_logger()
    init_db(app)
    rsbc_schemas.init_app(app)
    flags.init_app(app)
    gcp_queue.init_app(app)
    queue.init_app(app)
    babel.init_app(app)
    endpoints.init_app(app)

    with app.app_context():  # db require app context
        digital_credentials.init_app(app)

    cache.init_app(app)

    setup_jwt_manager(app, jwt)

    register_shellcontext(app)

    return app


def setup_jwt_manager(app, jwt_manager):
    """Use flask app to configure the JWTManager to work for a particular Realm."""
    def get_roles(a_dict):
        return a_dict['realm_access']['roles']  # pragma: no cover
    app.config['JWT_ROLE_CALLBACK'] = get_roles

    def custom_auth_error_handler(ex):
        response = jsonify(ex.error)
        response.status_code = ex.status_code
        response.headers['Access-Control-Allow-Origin'] = '*'
        return response
    app.config['JWT_OIDC_AUTH_ERROR_HANDLER'] = custom_auth_error_handler

    jwt_manager.init_app(app)


def register_shellcontext(app):
    """Register shell context objects."""
    def shell_context():
        """Shell context objects."""
        return {
            'app': app,
            'jwt': jwt,
            'db': db,
            'models': models}  # pragma: no cover

    app.shell_context_processor(shell_context)
