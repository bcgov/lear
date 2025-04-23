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
"""The Unit Tests for the Transition filing."""

import copy
import datetime
import random

from business_model.models import Filing
from registry_schemas.example_data import TRANSITION_FILING_TEMPLATE

from business_filer.filing_meta import FilingMeta
from business_filer.filing_processors import transition
from tests.unit import create_business, create_filing


def test_transition_filing_process(app, session):
    """Assert that the transition object is correctly populated to model objects."""
    # setup
    identifier = f'BC{random.randint(1000000,9999999)}'
    filing = copy.deepcopy(TRANSITION_FILING_TEMPLATE)
    filing['filing']['business']['identifier'] = identifier

    business = create_business(filing['filing']['business']['identifier'])
    create_filing('123', filing)

    effective_date = datetime.datetime.now(datetime.timezone.utc)
    filing_rec = Filing(effective_date=effective_date, filing_json=filing)
    filing_meta = FilingMeta(application_date=effective_date)

    # test
    transition.process(business, filing_rec, filing['filing'], filing_meta)

    # Assertions
    assert business.restriction_ind is False
    assert len(business.share_classes.all()) == len(filing['filing']['transition']['shareStructure']['shareClasses'])
    assert len(business.offices.all()) == len(filing['filing']['transition']['offices'])
    assert len(business.aliases.all()) == len(filing['filing']['transition']['nameTranslations'])
    assert len(business.resolutions.all()) == len(filing['filing']['transition']['shareStructure']['resolutionDates'])
    assert len(business.party_roles.all()) == 1
    assert len(filing_rec.filing_party_roles.all()) == 1
