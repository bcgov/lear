# Copyright © 2024 Province of British Columbia
#
# Licensed under the Apache License, Version 2.0 (the 'License');
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an 'AS IS' BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""This provides the service for involuntary dissolution."""
import pytz
from datedelta import datedelta
from sqlalchemy import exists, not_

from legal_api.models import Batch, BatchProcessing, Business, Filing, db
from legal_api.utils.datetime import datetime


class InvoluntaryDissolutionService():
    """Provides services to get information for involuntary dissolution."""

    @staticmethod
    def get_businesses_eligible_count():
        """Return the number of businesses eligible for involuntary dissolution."""
        eligible_types = [
            Business.LegalTypes.COMP.value,
            Business.LegalTypes.BC_ULC_COMPANY.value,
            Business.LegalTypes.BC_CCC.value,
            Business.LegalTypes.BCOMP.value,
            Business.LegalTypes.CONTINUE_IN.value,
            Business.LegalTypes.ULC_CONTINUE_IN.value,
            Business.LegalTypes.CCC_CONTINUE_IN.value,
            Business.LegalTypes.BCOMP_CONTINUE_IN.value,
            Business.LegalTypes.EXTRA_PRO_A.value,
            Business.LegalTypes.LIMITED_CO.value
        ]

        subquery = exists().where(BatchProcessing.business_id == Business.id,
                                  BatchProcessing.status != 'WITHDRAWN',
                                  BatchProcessing.batch_id == Batch.id,
                                  Batch.batch_type == 'INVOLUNTARY_DISSOLUTION')

        query = db.session.query(Business).\
            filter(Business.state == Business.State.ACTIVE).\
            filter(Business.legal_type.in_(eligible_types)).\
            filter(Business.no_dissolution.is_(False)).\
            filter(not_(subquery))

        results = query.all()

        seleted_count = 0
        for business in results:
            selected = False
            # selection criteria
            if _has_specific_filing_overdue(business):
                selected = True
            if _has_no_transition_filed_after_restoration(business):
                selected = True
            # exclusion criteria
            if _has_future_effective_filing(business):
                continue
            if _has_change_of_address_filing(business):
                continue
            if _has_delay_of_dissolution_filing(business):
                continue
            if _is_xpro_from_nwpta(business):
                continue
            if selected:
                seleted_count += 1

        return seleted_count


def _has_specific_filing_overdue(business: Business):
    """Check if the latest date of specific filings of the business is over 26 months.

    Return true if the date of filed recognition(IA)/restoration/annual report
    of the business is over 26 months, whichever is latest.
    """
    from legal_api.core.filing import Filing as CoreFiling  # pylint: disable=import-outside-toplevel
    # get recognition date
    latest_date = business.founding_date

    # get restoration date
    restoration_filings = Filing.get_filings_by_types(business.id,
                                                      [CoreFiling.FilingTypes.RESTORATION.value,
                                                       CoreFiling.FilingTypes.RESTORATIONAPPLICATION.value])
    if restoration_filings:
        latest_date = max(latest_date, restoration_filings[0].effective_date)

    # get last annual report date
    if business.last_ar_date:
        latest_date = max(latest_date, business.last_ar_date)

    latest_date_cutoff = latest_date + datedelta(years=2, months=2)
    if latest_date_cutoff.replace(tzinfo=pytz.UTC) < datetime.utcnow():
        return True

    return False


def _has_no_transition_filed_after_restoration(business: Business):
    """Check if the business has not filed transition within 12 months after restoration.

    Return true if the business needs to file Transition but does not file it in time, otherwise false.
    """
    from legal_api.core.filing import Filing as CoreFiling  # pylint: disable=import-outside-toplevel

    # skip checks if the business is Extraprovincial or BC Corps is incorporated or recognised on 2004-03-29 or later
    new_act_date = datetime(2004, 3, 29).replace(tzinfo=pytz.UTC)
    if business.legal_type == Business.LegalTypes.EXTRA_PRO_A.value or\
            business.founding_date >= new_act_date:
        return False

    # get latest restoration filing
    restoration_filings = Filing.get_filings_by_types(business.id,
                                                      [CoreFiling.FilingTypes.RESTORATION.value,
                                                       CoreFiling.FilingTypes.RESTORATIONAPPLICATION.value])
    if restoration_filings:
        latest_filing = restoration_filings[0]
        transition_date_cutoff = latest_filing.effective_date + datedelta(years=1)
        # get transition filing after the latest restoration
        trasition_filing = Filing.get_a_businesses_most_recent_filing_of_a_type(business.id,
                                                                                CoreFiling.FilingTypes.TRANSITION.value)
        if trasition_filing and\
                trasition_filing.effective_date >= latest_filing.effective_date and\
                trasition_filing.effective_date <= transition_date_cutoff:
            return False
        else:
            return True
    return False


def _has_future_effective_filing(business: Business):
    """Check if the business has future effective filings."""
    fed_filings = Filing.get_filings_by_status(business.id, [
        Filing.Status.PENDING, Filing.Status.PAID.value])
    return bool(fed_filings)


def _has_change_of_address_filing(business: Business):
    """Check if the business has Change of Address filings within last 32 days."""
    if business.last_coa_date:
        coa_date_cutoff = business.last_coa_date + datedelta(days=32)
        return coa_date_cutoff.replace(tzinfo=pytz.UTC) >= datetime.utcnow()
    return False


def _has_delay_of_dissolution_filing(business: Business):
    """Check if the business has Delay of Dissolution filing."""
    # TODO to implement in the future
    return False


def _is_xpro_from_nwpta(business: Business):
    """Check if the business is extraprovincial and from NWPTA jurisdictions."""
    if business.legal_type == Business.LegalTypes.EXTRA_PRO_A\
            and business.jurisdiction == 'CA'\
            and business.foreign_jurisdiction_region in [
                'AB', 'SK', 'MB'
            ]:
        return True
    return False
