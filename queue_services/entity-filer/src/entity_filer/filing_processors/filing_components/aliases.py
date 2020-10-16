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
from legal_api.models import Alias, Business


def update_aliases(business: Business, aliases: Dict) -> Dict:
    """Set the legal type of the business."""
    if not business:
        return {'error': babel('Business required before alternate names can be set.')}

    if ceased_aliases := aliases.get('ceased'):
        for current_alias in business.aliases.all():
            if current_alias.alias in ceased_aliases:
                business.aliases.remove(current_alias)

    if modified_aliases := aliases.get('modified'):
        for current_alias in business.aliases.all():
            for mod_alias in modified_aliases:
                if current_alias.alias.upper() == str(mod_alias.get('oldValue')).upper():
                    current_alias.alias = str(mod_alias.get('newValue')).upper()

    if new_aliases := aliases.get('new'):
        for new_alias in new_aliases:
            alias = Alias(alias=new_alias.upper(),
                          type=Alias.AliasType.TRANSLATION.value)
            business.aliases.append(alias)

    return None
