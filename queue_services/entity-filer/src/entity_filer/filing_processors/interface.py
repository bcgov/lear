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
"""File processing Interface definition to ensure processors implement both methods."""
from abc import ABC, abstractmethod

from legal_api.models import Business, Filing

class FilingProcessorInterface(ABC):
    """Defines the interface necessary for filing processors."""

    @abstractmethod
    def process(self, business: Business, filing: Filing):
        """Processes the filings contents and applies changes to the local datastore."""
        pass

    @abstractmethod
    def post_processing(self, business: Business, filing: Filing):
        """Finalize the filing and update any remote integrations."""
        pass