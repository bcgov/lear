# Copyright © 2021 Province of British Columbia
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
# limitations under the License
"""The business and its historical values.
This is the core business class.
It is used to represent a business and its historical values.
"""


class BusinessCommon:
    @property
    def is_alternate_name_entity(self):
        from legal_api.models import AlternateName

        return isinstance(self, AlternateName)

    @property
    def is_legal_entity(self):
        from legal_api.models import LegalEntity

        return isinstance(self, LegalEntity)

    @property
    def entity_type(self):
        """Return entity_type."""

        if self.is_legal_entity:
            return self._entity_type

        # TODO flesh this logic out fully
        return "SP"

    @property
    def compliance_warnings(self):
        """Return compliance warnings."""
        if not hasattr(self, "_compliance_warnings"):
            return []

        return self._compliance_warnings

    @compliance_warnings.setter
    def compliance_warnings(self, value):
        """Set compliance warnings."""
        self._compliance_warnings = value

    @property
    def warnings(self):
        """Return warnings."""
        if not hasattr(self, "_warnings"):
            return []

        return self._warnings

    @warnings.setter
    def warnings(self, value):
        """Set warnings."""
        self._warnings = value

    @property
    def allowable_actions(self):
        """Return warnings."""
        if not hasattr(self, "_allowable_actions"):
            return {}

        return self._allowable_actions

    @allowable_actions.setter
    def allowable_actions(self, value):
        """Set warnings."""
        self._allowable_actions = value
