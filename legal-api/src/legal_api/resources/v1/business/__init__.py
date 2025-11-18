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
"""Business Entity End-Points.

Provides all business entity externalized services.
"""

from .api_namespace import API
from .business import BusinessResource
from .business_address import AddressResource
from .business_aliases import AliasResource
from .business_comments import BusinessCommentResource
from .business_directors import DirectorResource
from .business_filings import ListFilingResource
from .business_resolutions import ResolutionResource
from .business_share_classes import ShareClassResource
from .business_tasks import TaskListResource
from .filing_comments import CommentResource
from .internal_services import InternalBusinessResource


__all__ = ("API",)
