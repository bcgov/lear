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
"""Business Entity Filings.

Provides all business entity Filings externalized services.
"""
from .business_documents import get_documents
from .business_filings import delete_filings, get_filings, patch_filings, saving_filings

__all__ = (
    "delete_filings",
    "get_documents",
    "get_filings",
    "patch_filings",
    "saving_filings",
    )
