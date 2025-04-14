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
"""Manages the  names of a Business."""
from typing import Dict

from flask_babel import _ as babel  # noqa: N813
from business_model.models import Alias, Business


def update_aliases(business: Business, aliases) -> Dict:
    """Update the aliases of the business."""
    if not business:
        return {'error': babel('Business required before alternate names can be set.')}

    for alias in aliases:
        if (alias_id := alias.get('id')) and \
                (existing_alias := next((x for x in business.aliases.all() if str(x.id) == alias_id), None)):
            existing_alias.alias = alias['name'].upper()
        else:
            new_alias = Alias(alias=alias['name'].upper(), type=Alias.AliasType.TRANSLATION.value)
            business.aliases.append(new_alias)

    for current_alias in business.aliases.all():
        if not next((x for x in aliases if x['name'].upper() == current_alias.alias.upper()), None):
            business.aliases.remove(current_alias)
    return None
