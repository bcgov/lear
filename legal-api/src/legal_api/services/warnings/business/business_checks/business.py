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

"""Service to check compliancy for a LegalEntity."""
from legal_api.models import LegalEntity
from .firms import check_business as firms_check  # noqa: I003


def check_business(legal_entity: any) -> list:
    """Check business for warnings."""
    result = []

    if legal_entity.entity_type in \
            (LegalEntity.EntityTypes.SOLE_PROP.value,
             LegalEntity.EntityTypes.PARTNERSHIP.value):
        result = firms_check(legal_entity)

    return result
