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
"""File processing rules and actions for the annual report."""
import datetime

from legal_api.models import Business, Filing


def process(business: Business, filing: Filing, submission_date: datetime.datetime):
    """Render the annual_report onto the business model objects."""
    agm_date = filing['annualReport'].get('annualGeneralMeetingDate')
    if agm_date:
        agm_date = datetime.date.fromisoformat(agm_date)
    business.last_agm_date = agm_date
    business.last_ar_date = submission_date
