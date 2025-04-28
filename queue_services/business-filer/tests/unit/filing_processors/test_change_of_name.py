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
"""The Unit Tests for the Change of Name filing."""
from business_filer.filing_meta import FilingMeta
from business_filer.filing_processors import change_of_name
from tests.unit import create_business


def test_change_of_name_process(app, session):
    """Assert that the legal name is changed."""
    # setup
    new_name = 'new legal_name'
    identifier = 'CP1234567'
    con = {'changeOfName': {'legalName': new_name}}

    business = create_business(identifier)
    business.legal_name = 'original name'

    filing_meta = FilingMeta()

    # test
    change_of_name.process(business, con, filing_meta)

    # validate
    assert business.legal_name == new_name


def test_change_of_name_with_nr_process(app, session):
    """Assert that the legal name is changed."""
    # setup
    new_name = 'new legal_name'
    identifier = 'CP1234567'
    con = {
        'changeOfName': {
            'nameRequest': {
                'nrNumber': 'NR 8798956',
                'legalName': new_name,
                'legalType': 'BC'
            }
        }
    }

    business = create_business(identifier)
    business.legal_name = 'original name'

    filing_meta = FilingMeta()

    # test
    change_of_name.process(business, con, filing_meta)

    # validate
    assert business.legal_name == new_name
