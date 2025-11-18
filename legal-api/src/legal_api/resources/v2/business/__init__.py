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
# limitations under the License.
"""Business Entity End-Points.

Provides all business entity externalized services.
"""
from .bp import bp  # noqa: I001
from .business import get_businesses, post_businesses
from .business_address import get_addresses
from .business_aliases import get_aliases
from .business_comments import get_comments, post_comments
from .business_directors import get_directors
from .business_documents import get_business_documents
from .business_filings import delete_filings, get_documents, get_filings, patch_filings, saving_filings
from .business_furnishings import get_furnishing_document
from .business_parties import get_parties
from .business_resolutions import get_resolutions
from .business_account_settings import get_business_account_settings, update_business_account_settings
from .business_share_classes import get_share_class
from .business_tasks import get_tasks
from .colin_sync import (
    get_all_identifiers_without_tax_id,
    get_colin_event_id,
    get_completed_filings_for_colin,
    set_tax_ids,
    update_colin_event_id,
    update_colin_id,
)
from .filing_comments import get_filing_comments, not_allowed_filing_comments, post_filing_comments


__all__ = ("bp",)
