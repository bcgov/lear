# Copyright © 2020 Province of British Columbia
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
"""Manages the type of Business."""
from typing import Dict

from flask_babel import _ as babel  # noqa: N813
from legal_api.models import Business


def set_corp_type(business: Business, business_info: Dict) -> Dict:
    """Set the legal type of the business."""
    if not business:
        return {'error': babel('Business required before type can be set.')}

    try:
        legal_type = business_info.get('legalType')
    except (IndexError, KeyError, TypeError):
        return {'error': babel('A valid legal type must be provided.')}

    business.legal_type = legal_type

    return None
