# Copyright © 2021 Columbia
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
"""Meta information about the service.

Currently this only provides API versioning information
"""
import os
from importlib.metadata import version

from flask import Blueprint, current_app, jsonify

from business_model.models import db
from legal_api.utils.run_version import get_run_version
from registry_schemas import __version__ as registry_schemas_version

bp = Blueprint("META2", __name__, url_prefix="/api/v2/meta")


@bp.route("/info")
def info():
    """Return a JSON object with meta information about the Service."""
    api_version = get_run_version()
    framework_version = version("flask")
    return jsonify(
        API=f"legal_api/{api_version}",
        SCHEMAS=f"registry_schemas/{registry_schemas_version}",
        FrameWork=f"{framework_version}")


@bp.route("/health")
def health():
    """Health check endpoint that verifies database connectivity."""
    try:
        # Simple query to verify DB connection
        db.session.execute(db.text("SELECT 1"))
        return jsonify({
            "status": "healthy",
            "database": "connected"
        }), 200
    except Exception as e:
        return jsonify({
            "status": "unhealthy",
            "database": "disconnected",
            "error": str(e)
        }), 503
