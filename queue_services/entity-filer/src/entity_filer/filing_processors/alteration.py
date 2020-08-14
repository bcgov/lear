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
from contextlib import suppress
from typing import Dict

import dpath
import sentry_sdk
from legal_api.models import Business, Filing

from entity_filer.filing_processors.filing_components import aliases, business_info, business_profile


def process(business: Business, filing: Dict):
    """Render the Alteration onto the model objects."""
    # Alter the corp type, if any
    with suppress(IndexError, KeyError, TypeError):
        business_json = dpath.util.get(filing, '/alteration/business')
        business_info.set_corp_type(business, business_json)

    # update name translations, if any
    with suppress(IndexError, KeyError, TypeError):
        business_json = dpath.util.get(filing, '/alteration/nameTranslations')
        aliases.update_aliases(business, business_json)


def post_process(business: Business, filing: Filing):
    """Post processing activities for incorporations.

    THIS SHOULD NOT ALTER THE MODEL
    """
    with suppress(IndexError, KeyError, TypeError):
        err = business_profile.update_business_profile(
            business,
            filing.json['filing']['incorporationApplication']['contactPoint']
        )
        sentry_sdk.capture_message(f'Queue Error: Update Business for filing:{filing.id},  error:{err}', level='error')
