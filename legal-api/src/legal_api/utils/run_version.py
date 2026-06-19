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
"""Supply version and commit hash info."""
import os
from importlib.metadata import version


def _get_commit_hash():
    """Return the containers ref if present."""
    if (commit_hash := os.getenv("VCS_REF", None)) and commit_hash != "missing":
        return commit_hash
    return None


def get_run_version():
    """Return a formatted version string for this service."""
    ver = version(__name__[: __name__.find(".")])
    if commit_hash := _get_commit_hash():
        return f"{ver}-{commit_hash}"
    return ver
