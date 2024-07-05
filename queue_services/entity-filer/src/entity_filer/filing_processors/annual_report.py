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
from contextlib import suppress
from typing import Dict

from entity_queue_common.service_utils import logger
from legal_api.models import BatchProcessing, Business
from legal_api.services.filings import validations
from legal_api.services.involuntary_dissolution import InvoluntaryDissolutionService

from entity_filer.filing_meta import FilingMeta


def process(business: Business, filing: Dict, filing_meta: FilingMeta, flag_on):
    """Render the annual_report onto the business model objects."""
    legal_filing_name = 'annualReport'
    agm_date = filing[legal_filing_name].get('annualGeneralMeetingDate')
    ar_date = filing[legal_filing_name].get('annualReportDate')

    if ar_date:
        ar_date = datetime.date.fromisoformat(ar_date)
    else:
        # should never get here (schema validation should prevent this from making it to the filer)
        logger.error('No annualReportDate given for in annual report. Filing id: %s', filing.id)

    business.last_ar_date = ar_date
    if agm_date and validations.annual_report.requires_agm(business):
        with suppress(ValueError):
            agm_date = datetime.date.fromisoformat(agm_date)
            business.last_agm_date = agm_date
            business.last_ar_date = agm_date

    business.last_ar_year = business.last_ar_year + 1 if business.last_ar_year else business.founding_date.year + 1

    # remove dissolution flag if business can be withdrawn
    if flag_on and business.in_dissolution:
        eligibility, _ = InvoluntaryDissolutionService.check_business_eligibility(
            business.identifier,
            InvoluntaryDissolutionService.EligibilityFilters(exclude_in_dissolution=False)
            )
        if not eligibility:
            batch_processing, _ = InvoluntaryDissolutionService.get_in_dissolution_batch_processing(business.id)
            batch_processing.status = BatchProcessing.BatchProcessingStatus.WITHDRAWN.value
            batch_processing.notes = 'Moved back to good standing'
            batch_processing.last_modified = datetime.datetime.utcnow()

    # save the annual report date to the filing meta info
    filing_meta.application_date = ar_date
    filing_meta.annual_report = {'annualReportDate': ar_date.isoformat(),
                                 'annualGeneralMeetingDate': agm_date,
                                 'annualReportFilingYear': business.last_ar_year}
