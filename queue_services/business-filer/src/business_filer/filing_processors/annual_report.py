# Copyright © 2025 Province of British Columbia
#
# Licensed under the BSD 3 Clause License, (the "License");
# you may not use this file except in compliance with the License.
# The template for the license can be found here
#    https://opensource.org/license/bsd-3-clause/
#
# Redistribution and use in source and binary forms,
# with or without modification, are permitted provided that the
# following conditions are met:
#
# 1. Redistributions of source code must retain the above copyright notice,
#    this list of conditions and the following disclaimer.
#
# 2. Redistributions in binary form must reproduce the above copyright notice,
#    this list of conditions and the following disclaimer in the documentation
#    and/or other materials provided with the distribution.
#
# 3. Neither the name of the copyright holder nor the names of its contributors
#    may be used to endorse or promote products derived from this software
#    without specific prior written permission.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS “AS IS”
# AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO,
# THE IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE
# ARE DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT HOLDER OR CONTRIBUTORS BE
# LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR
# CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF
# SUBSTITUTE GOODS OR SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS
# INTERRUPTION) HOWEVER CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN
# CONTRACT, STRICT LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE)
# ARISING IN ANY WAY OUT OF THE USE OF THIS SOFTWARE, EVEN IF ADVISED OF THE
# POSSIBILITY OF SUCH DAMAGE.
"""File processing rules and actions for the annual report."""
import datetime
from contextlib import suppress

from business_model.models import BatchProcessing, Business
from flask import current_app

from business_filer.common.services import InvoluntaryDissolutionService
from business_filer.exceptions import FilingException
from business_filer.filing_meta import FilingMeta


def process(business: Business, filing: dict, filing_meta: FilingMeta, flag_on):
    """Render the annual_report onto the business model objects."""
    legal_filing_name = "annualReport"

    # set ar_date or bail
    try:
       ar_date = filing[legal_filing_name].get("annualReportDate")
       ar_date = datetime.date.fromisoformat(ar_date)
    except (TypeError, ValueError) as err:
        # This should never happen
        current_app.logger.error("No annualReportDate given for in annual report. Filing id: %s", filing.id)
        raise FilingException("No annualReportDate given for in annual report. Filing id: %s", filing.id) from err
    business.last_ar_date = ar_date
    
    # if there's an agm date, set it
    agm_date = None
    with suppress(ValueError, TypeError):
        agm_date = datetime.date.fromisoformat(
            filing[legal_filing_name].get("annualGeneralMeetingDate", None)
        )
    business.last_agm_date = agm_date

    # increment the last year
    business.last_ar_year = business.last_ar_year + 1 if business.last_ar_year else business.founding_date.year + 1

    # remove dissolution flag if business can be withdrawn
    if flag_on and business.in_dissolution:
        eligibility, _ = InvoluntaryDissolutionService.check_business_eligibility(
            business.identifier,
            InvoluntaryDissolutionService.EligibilityFilters(
                    exclude_in_dissolution=False, exclude_future_effective_filing=True
                )
            )
        if not eligibility:
            batch_processing, _ = InvoluntaryDissolutionService.get_in_dissolution_batch_processing(business.id)
            batch_processing.status = BatchProcessing.BatchProcessingStatus.WITHDRAWN.value
            batch_processing.notes = "Moved back into good standing"
            batch_processing.last_modified = datetime.datetime.now(datetime.UTC)

    # save the annual report date to the filing meta info
    filing_meta.application_date = ar_date
    filing_meta.annual_report = {"annualReportDate": ar_date.isoformat(),
                                 "annualGeneralMeetingDate": agm_date,
                                 "annualReportFilingYear": business.last_ar_year}
