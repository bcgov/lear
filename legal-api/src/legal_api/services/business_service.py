# Copyright © 2022 Province of British Columbia
#
# Licensed under the Apache License, Version 2.0 (the 'License');
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an 'AS IS' BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""This provides the service for businesses(legal entities and alternate name entities."""
from legal_api.models import LegalEntity


class BusinessService:
    """Provides services to retrieve correct businesses."""


    def fetch_business(self, identifier):
        legal_entity, alternate_name_entity = LegalEntity.find_by_identifier(identifier)
        if alternate_name_entity:
            return alternate_name_entity
        return legal_entity
