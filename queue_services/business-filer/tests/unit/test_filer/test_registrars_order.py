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
"""The Unit Tests for the Registrars Order filing."""
import copy
import random

from business_model.models import Filing
from registry_schemas.example_data import REGISTRARS_ORDER_FILING_TEMPLATE

from business_filer.services.filer import process_filing
from tests.unit import create_business, create_filing
from business_filer.common.filing_message import FilingMessage
from business_filer.common.filing_message import dict_keys_to_snake_case




def tests_filer_registrars_order(app, session):
    """Assert that the registrars order object is correctly populated to model objects."""
    identifier = 'BC1234567'
    business = create_business(identifier, legal_type='BC')

    filing = copy.deepcopy(REGISTRARS_ORDER_FILING_TEMPLATE)
    filing['filing']['business']['identifier'] = identifier

    payment_id = str(random.SystemRandom().getrandbits(0x58))
    filing_id = (create_filing(payment_id, filing, business_id=business.id)).id

    filing_msg = FilingMessage(filing_identifier=filing_id)
    
    # Test
    process_filing(filing_msg)

    # Check outcome
    final_filing = Filing.find_by_id(filing_id)
    assert filing['filing']['registrarsOrder']['fileNumber'] == final_filing.court_order_file_number
    assert filing['filing']['registrarsOrder']['effectOfOrder'] == final_filing.court_order_effect_of_order
    assert filing['filing']['registrarsOrder']['orderDetails'] == final_filing.order_details
