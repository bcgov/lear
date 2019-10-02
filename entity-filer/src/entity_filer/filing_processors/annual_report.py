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
from legal_api.services.filings import validations

from entity_filer.service_utils import logger


def process(business: Business, filing: Filing):
    """Render the annual_report onto the business model objects."""
    agm_date = filing['annualReport'].get('annualGeneralMeetingDate')
    ar_date = filing['annualReport'].get('annualReportDate')
    if agm_date and validations.annual_report.requires_agm(business):
        agm_date = datetime.date.fromisoformat(agm_date)
    if ar_date:
        ar_date = datetime.date.fromisoformat(ar_date)
    else:
        # should never get here (schema validation should prevent this from making it to the filer)
        logger.error('No annualReportDate given for in annual report. Filing id: %s', filing.id)
    business.last_agm_date = agm_date
    business.last_ar_date = ar_date
