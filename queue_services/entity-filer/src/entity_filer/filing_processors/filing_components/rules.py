# Copyright © 2022 Province of British Columbia
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
"""Manages the share structure for a business."""
from __future__ import annotations

from typing import Dict, List, Optional

from dateutil.parser import parse
from legal_api.models import Business, Resolution, ShareClass, ShareSeries


def update_rules(business: Business, share_structure: Dict) -> Optional[List]:
    """Manage the share structure for a business.

    Assumption: The structure has already been validated, upon submission.

    Other errors are recorded and will be managed out of band.
    """
    if not business or not share_structure:
        # if nothing is passed in, we don't care and it's not an error
        return None

    err = []

    return err