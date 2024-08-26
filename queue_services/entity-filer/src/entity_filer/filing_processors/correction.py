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
"""File processing rules and actions for the correction filing."""
from typing import Dict

import pytz
from legal_api.models import Business, Comment, Filing

from entity_filer.filing_meta import FilingMeta
from entity_filer.filing_processors.filing_components.correction import correct_business_data


def process(correction_filing: Filing, filing: Dict, filing_meta: FilingMeta, business: Business):
    """Render the correction filing onto the business model objects."""
    local_timezone = pytz.timezone('US/Pacific')

    # link to original filing
    original_filing = Filing.find_by_id(filing['correction']['correctedFilingId'])
    original_filing.parent_filing = correction_filing

    # add comment to the original filing
    original_filing.comments.append(
        Comment(
            comment=f'This filing was corrected on '
                    f'{correction_filing.filing_date.astimezone(local_timezone).date().isoformat()}.',
            staff_id=correction_filing.submitter_id
        )
    )

    # add comment to the correction filing
    correction_filing.comments.append(
        Comment(
            comment=filing['correction']['comment'],
            staff_id=correction_filing.submitter_id
        )
    )

    corrected_filing_type = filing['correction']['correctedFilingType']
    if corrected_filing_type != 'conversion':
        correct_business_data(business, correction_filing, filing, filing_meta)
    else:
        # set correction filing to PENDING_CORRECTION, for manual intervention
        # - include flag so that listener in Filing model does not change state automatically to COMPLETE
        correction_filing._status = Filing.Status.PENDING_CORRECTION.value  # pylint: disable=protected-access
        setattr(correction_filing, 'skip_status_listener', True)

    original_filing.save_to_session()
    return correction_filing
