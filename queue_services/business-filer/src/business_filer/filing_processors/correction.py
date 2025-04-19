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
"""File processing rules and actions for the correction filing."""
from typing import Dict

import dpath
import pytz
from business_model.models import Business, Comment, Filing

from business_filer.filing_meta import FilingMeta
from business_filer.filing_processors.filing_components.correction import correct_business_data


def process(correction_filing: Filing, filing: Dict, filing_meta: FilingMeta, business: Business):
    """Render the correction filing onto the business model objects."""
    local_timezone = pytz.timezone('US/Pacific')

    # link to original filing
    original_filing = Filing.find_by_id(filing['correction']['correctedFilingId'])
    original_filing.parent_filing = correction_filing

    filing_meta.correction = {}

    # add comment to the original filing
    original_filing.comments.append(
        Comment(
            comment=f'This filing was corrected on '
                    f'{correction_filing.filing_date.astimezone(local_timezone).date().isoformat()}.',
            staff_id=correction_filing.submitter_id
        )
    )

    original_filing.save_to_session()

    # add comment to the correction filing
    correction_filing.comments.append(
        Comment(
            comment=filing['correction']['comment'],
            staff_id=correction_filing.submitter_id
        )
    )

    corrected_filing_type = filing['correction']['correctedFilingType']

    # check if empty correction and set commentOnly value in filing_meta
    if bool(dpath.util.get(filing, '/correction/commentOnly', default=None)):
        filing_meta.correction = {**filing_meta.correction, 'commentOnly': True}
        return correction_filing

    # Skip all other data checks if commentOnly correction
    if corrected_filing_type != 'conversion':
        correct_business_data(business, correction_filing, filing, filing_meta)
    else:
        # set correction filing to PENDING_CORRECTION, for manual intervention
        # - include flag so that listener in Filing model does not change state automatically to COMPLETE
        correction_filing._status = Filing.Status.PENDING_CORRECTION.value  # pylint: disable=protected-access
        setattr(correction_filing, 'skip_status_listener', True)

    return correction_filing
