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
"""Tests to ensure the job works as expected."""
from http import HTTPStatus

from update_colin_filings.worker import run

from . import get_mocked_colin_resp, get_mocked_lear_resp


def test_worker_run(requests_mock, app):
    """Ensure the worker run function runs successfully."""
    filing_id = 987
    filing_name = "annualReport"
    identifier = "BC1234567"
    legal_type = "BEN"
    colin_ids = [1, 2, 3]
    # auth token mock
    auth_mock = requests_mock.post(app.config.get("ACCOUNT_SVC_AUTH_URL"), json={"access_token": "token"})
    # lear get outstanding filings mock
    lear_get_url = f'{app.config["LEAR_SVC_URL"]}/businesses/internal/filings?offset=0&limit=50'
    get_filings_mock = requests_mock.get(lear_get_url, json=get_mocked_lear_resp(filing_id, filing_name, identifier, legal_type))
    # colin post filing mock
    colin_url = f'{app.config["COLIN_SVC_URL"]}/businesses/{legal_type}/{identifier}/filings/{filing_name}'
    update_colin_mock = requests_mock.post(colin_url, json=get_mocked_colin_resp(colin_ids), status_code=HTTPStatus.CREATED)
    # lear patch colin ids mock
    lear_patch_url = f'{app.config["LEAR_SVC_URL"]}/businesses/internal/filings/{filing_id}'
    update_ids_mock = requests_mock.patch(lear_patch_url, status_code=HTTPStatus.ACCEPTED)

    # test with mocked urls
    run()

    assert auth_mock.called
    assert get_filings_mock.called
    assert update_colin_mock.called
    # assert patch mock was called with expected colin_ids
    assert update_ids_mock.called
    assert update_ids_mock.request_history[0].json() == {"colinIds": colin_ids}
    
    
