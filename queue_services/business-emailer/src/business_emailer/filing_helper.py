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
"""Helper function for filings."""


def is_special_resolution_correction_by_filing_json(filing: dict):
    """Check whether it is a special resolution correction."""
    # Note this relies on the filing data once. This is acceptable inside of the filer (which runs once)
    # and emailer (runs on PAID which is before the filer and runs on COMPLETED).
    # For filing data that persists in the database, attempt to use the meta_data instead.
    sr_correction_keys = ["rulesInResolution", "resolution", "rulesFileKey", "memorandumFileKey",
                          "memorandumInResolution", "cooperativeAssociationType"]
    for key in sr_correction_keys:
        if key in filing.get("correction"):
            return True
    return "requestType" in filing.get("correction", {}).get("nameRequest", {})
