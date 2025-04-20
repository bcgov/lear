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
"""The Test Suites to ensure that the worker is operating correctly."""
import copy
import random

from business_model.models import Business, Filing, PartyRole
from registry_schemas.example_data import TRANSITION_FILING_TEMPLATE, FILING_HEADER, TRANSITION

from business_filer.services.filer import process_filing
from tests.unit import create_business, create_filing


def test_transition_filing(app, session):
    """Assert we can create a business based on transition filing."""
    filing_data = copy.deepcopy(FILING_HEADER)
    filing_data['filing']['transition'] = copy.deepcopy(TRANSITION)

    business = create_business(filing_data['filing']['business']['identifier'])

    payment_id = str(random.SystemRandom().getrandbits(0x58))
    filing = (create_filing(payment_id, filing_data, business.id))

    filing_msg = {'filing': {'id': filing.id}}

    # Test
    process_filing(filing_msg)

    # Check outcome
    filing = Filing.find_by_id(filing.id)
    business = Business.find_by_internal_id(filing.business_id)

    filing_json = filing.filing_json
    assert business
    assert filing
    assert filing.status == Filing.Status.COMPLETED.value
    assert business.restriction_ind is False
    assert len(business.share_classes.all()) == len(filing_json['filing']['transition']['shareStructure']
                                                    ['shareClasses'])
    assert len(business.offices.all()) == len(filing_json['filing']['transition']['offices'])
    assert len(business.aliases.all()) == len(filing_json['filing']['transition']['nameTranslations'])
    assert len(business.resolutions.all()) == len(filing_json['filing']['transition']['shareStructure']
                                                  ['resolutionDates'])
    assert len(PartyRole.get_parties_by_role(business.id, 'director')) == 1
