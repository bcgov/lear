# Copyright © 2019 Province of British Columbia
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
"""File processing rules and actions for the Change of Name filing."""
from typing import Tuple

from entity_queue_common.service_utils import logger
from legal_api.exceptions import BusinessException
from legal_api.models import Business, Filing

from entity_filer.filing_processors.filing_components import set_corp_type


def process(business: Business, filing: Filing) -> Tuple[Business, Filing]:
    """Render the Alteration onto the model objects."""
    logger.debug('processing Alteration: %s', filing.id)
    # alterCorpType
    try:
        corpType = str(filing.filing_json['filing']['alteration']['alterCorpType']['corpType'])
        set_corp_type(business, corpType)

    except KeyError:
        pass
    except BusinessException as be:
        pass

    # alterCorpName
    # alterNameTranslations
    # alterShareStructure
    return business, filing


def post_processing(self, business: Business, filing: Filing):
    """Finalize the filing and update any remote integrations."""
    pass
    # alterCorpType
    # alterCorpName
    # alterNameTranslations
    # alterShareStructure
