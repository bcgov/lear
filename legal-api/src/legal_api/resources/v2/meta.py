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

from flask import Blueprint
from flask import __version__ as framework_version
from flask import jsonify
from registry_schemas import __version__ as registry_schemas_version

from legal_api.utils.run_version import get_run_version


bp = Blueprint("META2", __name__, url_prefix="/api/v2/meta")


@bp.route("/info")
def info():
    """Return a JSON object with meta information about the Service."""
    version = get_run_version()
    return jsonify(
        API=f"legal_api/{version}",
        SCHEMAS=f"registry_schemas/{registry_schemas_version}",
        FrameWork=f"{framework_version}",
    )
