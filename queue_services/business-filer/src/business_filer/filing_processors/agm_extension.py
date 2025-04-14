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
"""File processing rules and actions for the agm extension filing."""

from typing import Dict

import dpath

from business_filer.filing_meta import FilingMeta


def process(filing: Dict, filing_meta: FilingMeta):
    """Render the agm extension filing onto the business model objects."""
    filing_meta.agm_extension = {
        'year': filing['agmExtension']['year'],
        'isFirstAgm': filing['agmExtension']['isFirstAgm'],
        'extReqForAgmYear': filing['agmExtension']['extReqForAgmYear'],
        'totalApprovedExt': filing['agmExtension']['totalApprovedExt'],
        'extensionDuration': filing['agmExtension']['extensionDuration'],
        'isFinalExtension': _check_final_extension(filing)
    }

    if prev_agm_ref_date := dpath.util.get(filing, '/agmExtension/prevAgmRefDate', default=None):
        filing_meta.agm_extension = {
            **filing_meta.agm_extension,
            'prevAgmRefDate': prev_agm_ref_date
        }

    if curr_ext_expiry_date := dpath.util.get(filing, '/agmExtension/expireDateCurrExt', default=None):
        filing_meta.agm_extension = {
            **filing_meta.agm_extension,
            'expireDateCurrExt': curr_ext_expiry_date
        }

    if expiry_date_approved_ext := dpath.util.get(filing, '/agmExtension/expireDateApprovedExt', default=None):
        filing_meta.agm_extension = {
            **filing_meta.agm_extension,
            'expireDateApprovedExt': expiry_date_approved_ext
        }


def _check_final_extension(filing: Dict) -> bool:
    """Mark final extension for current agm year."""
    total_approved_ext = filing['agmExtension']['totalApprovedExt']
    if total_approved_ext >= 12:
        return True
    return False
