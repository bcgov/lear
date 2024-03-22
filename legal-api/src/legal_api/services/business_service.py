# Copyright © 2024 Province of British Columbia
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
from legal_api.models import AlternateName, LegalEntity
from legal_api.models.business_common import BusinessCommon


class BusinessService:
    """Provides services to retrieve correct businesses."""

    @staticmethod
    def fetch_business(identifier: str):
        """Fetches appropriate business.

        This can be an instance of legal entity or alternate name.
        """
        if identifier.startswith("T"):
            return None
        if legal_entity := LegalEntity.find_by_identifier(identifier):
            return legal_entity

        if identifier.startswith("FM") and (alternate_name := AlternateName.find_by_identifier(identifier)):
            if alternate_name.is_owned_by_colin_entity:
                return alternate_name

            legal_entity = LegalEntity.find_by_id(alternate_name.legal_entity_id)
            alternate_name_entity = (
                alternate_name if legal_entity.entity_type != BusinessCommon.EntityTypes.PARTNERSHIP.value else None
            )
            return alternate_name_entity

        return None

    @staticmethod
    def fetch_business_by_filing(filing):  # pylint: disable=redefined-builtin
        """Fetches appropriate business from a filing.

        This can be an instance of legal entity or alternate name.
        """
        if (legal_entity_id := filing.legal_entity_id) and (
            legal_entity := LegalEntity.find_by_internal_id(legal_entity_id)
        ):
            return legal_entity

        if (alternate_name_id := filing.alternate_name_id) and (
            alternate_name := AlternateName.find_by_internal_id(alternate_name_id)
        ):
            if alternate_name.is_owned_by_colin_entity:
                return alternate_name

            legal_entity = LegalEntity.find_by_id(alternate_name.legal_entity_id)
            alternate_name_entity = (
                alternate_name if legal_entity.entity_type != BusinessCommon.EntityTypes.PARTNERSHIP.value else None
            )
            return alternate_name_entity

        return None

    @staticmethod
    def fetch_business_by_tax_id(old_bn: str):
        """Fetches appropriate business by tax_id or bn15

        This can be an instance of legal entity or alternate name.
        """
        non_business_types = [
            LegalEntity.EntityTypes.PERSON.value,
            LegalEntity.EntityTypes.ORGANIZATION.value,
        ]

        if legal_entity := LegalEntity.find_by_tax_id(old_bn):
            return legal_entity if legal_entity.entity_type not in (non_business_types) else None

        if alternate_name := AlternateName.find_by_tax_id(old_bn):
            return alternate_name

        return None
