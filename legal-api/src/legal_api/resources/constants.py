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
"""Constants used in managing the end-points."""
from __future__ import annotations

from enum import Enum


class EndpointEnum(str, Enum):
    """Enumerate the endpoint mounts used in the system."""

    API_V1 = "/api/v1"
    API_V2 = "/api/v2"
    API = "/api"
    BUSINESSES_V2 = "/api/v2/businesses"
    DEFAULT_API = API_V1
    ADMIN_V2 = "/api/v2/admin"


class EndpointVersionEnum(str, Enum):
    """Enumerate the Accept Version Headers."""

    V1 = "v1"
    V2 = "v2"
