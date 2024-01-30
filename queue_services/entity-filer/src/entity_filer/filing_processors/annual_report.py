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

# TODO use structured logger
# from entity_queue_common.service_utils import logger
from business_model import LegalEntity

from entity_filer.filing_meta import FilingMeta

# from legal_api.services.filings import validations



def process(legal_entity: LegalEntity, filing: Dict, filing_meta: FilingMeta):
    """Render the annual_report onto the legal_entity model objects."""
    legal_filing_name = "annualReport"
    # agm_date = filing[legal_filing_name].get('annualGeneralMeetingDate')
    ar_date = filing[legal_filing_name].get("annualReportDate")

    if ar_date:
        ar_date = datetime.date.fromisoformat(ar_date)
    else:
        # should never get here (schema validation should prevent this from making it to the filer)
        print("No annualReportDate given for in annual report. Filing id: %s", filing.id)

    legal_entity.last_ar_date = ar_date
    # Validations are on input
    # if there is an AGM set, assume it is required and valid,
    # otherwise the Validator has failed.
    # TODO remove this
    # if agm_date and validations.annual_report.requires_agm(legal_entity):
    if agm_date := filing[legal_filing_name].get("annualGeneralMeetingDate"):
        with suppress(ValueError):
            agm_date = datetime.date.fromisoformat(agm_date)
            legal_entity.last_agm_date = agm_date
            legal_entity.last_ar_date = agm_date

    legal_entity.last_ar_year = (
        legal_entity.last_ar_year + 1 if legal_entity.last_ar_year else legal_entity.founding_date.year + 1
    )

    # save the annual report date to the filing meta info
    filing_meta.application_date = ar_date
    filing_meta.annual_report = {
        "annualReportDate": ar_date.isoformat(),
        "annualGeneralMeetingDate": agm_date,
        "annualReportFilingYear": legal_entity.last_ar_year,
    }
