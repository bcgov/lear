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
"""The Admin End-Point Blueprint.

Provides the mount point for all of the admin end-points.
"""

from flask import Blueprint

from legal_api.resources.constants import EndpointEnum

bp_admin = Blueprint("ADMIN_V2", __name__, url_prefix=EndpointEnum.ADMIN_V2)
