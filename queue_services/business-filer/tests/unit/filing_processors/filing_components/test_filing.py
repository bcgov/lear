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
"""The Unit Tests for the Name Request filing component."""
import copy
from datetime import datetime
from typing import Final

from registry_schemas.example_data import ALTERATION_FILING_TEMPLATE

from business_filer.filing_processors.filing_components import filings
from tests.unit import create_filing


def test_update_filing_court_order(app, session):
    """Assert that the new aliases are created."""
    # setup
    file_number: Final  = '#1234-5678/90'
    order_date: Final = '2021-01-30T09:56:01+08:00'
    effect_of_order: Final  = 'hasPlan'

    filing = copy.deepcopy(ALTERATION_FILING_TEMPLATE)
    alteration_filing = create_filing(token='123', json_filing=filing)
    court_order_json= {'courtOrder':
                                   {
                                       'fileNumber': file_number,
                                       'orderDate': order_date,
                                       'effectOfOrder': effect_of_order
                                    }
    }

    # test
    filings.update_filing_court_order(alteration_filing, court_order_json['courtOrder'])

    # validate
    assert file_number == alteration_filing.court_order_file_number
    assert datetime.fromisoformat(order_date) == alteration_filing.court_order_date
    assert effect_of_order == alteration_filing.court_order_effect_of_order
    
