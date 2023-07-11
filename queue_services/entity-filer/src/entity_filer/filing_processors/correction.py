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
from contextlib import suppress
from typing import Dict

import pytz
import sentry_sdk
from legal_api.models import Business, Comment, Filing

from entity_filer.filing_meta import FilingMeta
from entity_filer.filing_processors.filing_components import business_profile, name_request
from entity_filer.filing_processors.filing_components.correction import correct_business_data


def filer_is_special_resolution_correction(filing: Dict):
    """Check whether it is a special resolution correction."""
    # Note this relies on the filing data once. This is acceptable inside of the filer (which runs once).
    # For filing data that persists in the database, attempt to use the metadata instead.
    sr_correction_keys = ['rulesInResolution', 'resolution', 'rulesFileKey',
                          'memorandumInResolution', 'associationType']
    for key in sr_correction_keys:
        if key in filing.get('correction'):
            return True
    if 'requestType' in filing.get('correction', {}).get('nameRequest', {}):
        return True
    return False


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
    is_sr_correction = business.legal_type == 'CP' and filer_is_special_resolution_correction(filing)
    if (business.legal_type in ['SP', 'GP', 'BC', 'BEN', 'CC', 'ULC'] or
            is_sr_correction) and \
            corrected_filing_type != 'conversion':
        correct_business_data(business, correction_filing, filing, filing_meta)
    else:
        # set correction filing to PENDING_CORRECTION, for manual intervention
        # - include flag so that listener in Filing model does not change state automatically to COMPLETE
        correction_filing._status = Filing.Status.PENDING_CORRECTION.value  # pylint: disable=protected-access
        setattr(correction_filing, 'skip_status_listener', True)

    original_filing.save_to_session()
    return correction_filing


def post_process(business: Business, filing: Filing):
    """Post processing activities for correction.

    THIS SHOULD NOT ALTER THE MODEL
    """
    name_request.consume_nr(business, filing, 'correction')

    with suppress(IndexError, KeyError, TypeError):
        if err := business_profile.update_business_profile(
            business,
            filing.json['filing']['correction']['contactPoint']
        ):
            sentry_sdk.capture_message(
                f'Queue Error: Update Business for filing:{filing.id},error:{err}',
                level='error')
