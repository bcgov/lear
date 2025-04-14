# Copyright © 2023 Province of British Columbia
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
"""File processing rules and actions for the agm location change filing."""

from typing import Dict

from business_filer.filing_meta import FilingMeta


def process(filing: Dict, filing_meta: FilingMeta):
    """Render the agm location change filing into the model objects."""
    filing_meta.agm_location_change = {
        'year': filing['agmLocationChange']['year'],
        'agmLocation': filing['agmLocationChange']['agmLocation'],
        'reason': filing['agmLocationChange']['reason']
    }
