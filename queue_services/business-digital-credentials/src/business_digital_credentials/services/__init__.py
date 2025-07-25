# Copyright © 2025 Province of British Columbia
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
"""Services used by Business-Digital-Credentials."""
from gcp_queue import GcpQueue

from .flags import Flags

flags = Flags()
gcp_queue = GcpQueue()


def create_filing_msg(identifier):
    """Create the filing payload."""
    filing_msg = {"filing": {"id": identifier}}
    return filing_msg


def create_gcp_filing_msg(identifier):
    """Create the GCP filing payload."""
    filing_msg = {"filingMessage": {"filingIdentifier": identifier}}
    return filing_msg