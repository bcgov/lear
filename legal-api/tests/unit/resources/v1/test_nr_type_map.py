# Copyright © 2021 Province of British Columbia
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

"""Tests to assure the Name Request Type mapping service.

Test suite to ensure that the /nrTypeMap endpoint is working as expected.
"""
import json
import pytest


CR_RESULTS = [
    {'nrTypeCd': 'CR', 'entityTypeCd': 'BC', 'requestActionCd': 'NEW_AML'},
    {'nrTypeCd': 'CR', 'entityTypeCd': 'BC', 'requestActionCd': 'NEW'},
    {'nrTypeCd': 'CR', 'entityTypeCd': 'BC', 'requestActionCd': 'AML'}
]

BC_RESULTS = [
    {'nrTypeCd': 'CR', 'entityTypeCd': 'BC', 'requestActionCd': 'NEW_AML'},
    {'nrTypeCd': 'CR', 'entityTypeCd': 'BC', 'requestActionCd': 'NEW'},
    {'nrTypeCd': 'CR', 'entityTypeCd': 'BC', 'requestActionCd': 'AML'},
    {'nrTypeCd': 'CCR', 'entityTypeCd': 'BC', 'requestActionCd': 'CHG'},
    {'nrTypeCd': 'CT', 'entityTypeCd': 'BC', 'requestActionCd': 'MVE'},
    {'nrTypeCd': 'RCR', 'entityTypeCd': 'BC', 'requestActionCd': 'REST'},
    {'nrTypeCd': 'RCR', 'entityTypeCd': 'BC', 'requestActionCd': 'REH'},
    {'nrTypeCd': 'RCR', 'entityTypeCd': 'BC', 'requestActionCd': 'REN'},
    {'nrTypeCd': 'BECR', 'entityTypeCd': 'BC', 'requestActionCd': 'CNV'},
    {'nrTypeCd': 'ULCB', 'entityTypeCd': 'BC', 'requestActionCd': 'CNV'}
]

NEW_RESULTS = [
    {'nrTypeCd': 'CR', 'entityTypeCd': 'BC', 'requestActionCd': 'NEW'},
    # {'nrTypeCd': 'XCR', 'entityTypeCd': 'XCR', 'requestActionCd': 'NEW'},
    {'nrTypeCd': 'LC', 'entityTypeCd': 'XL', 'requestActionCd': 'NEW'},
    {'nrTypeCd': 'FR', 'entityTypeCd': 'SP', 'requestActionCd': 'NEW'},
    {'nrTypeCd': 'FR', 'entityTypeCd': 'GP', 'requestActionCd': 'NEW'},
    # {'nrTypeCd': 'FR', 'entityTypeCd': 'DBA', 'requestActionCd': 'NEW'},
    {'nrTypeCd': 'LL', 'entityTypeCd': 'LL', 'requestActionCd': 'NEW'},
    {'nrTypeCd': 'XLL', 'entityTypeCd': 'XL', 'requestActionCd': 'NEW'},
    {'nrTypeCd': 'LP', 'entityTypeCd': 'LP', 'requestActionCd': 'NEW'},
    {'nrTypeCd': 'XLP', 'entityTypeCd': 'XP', 'requestActionCd': 'NEW'},
    {'nrTypeCd': 'SO', 'entityTypeCd': 'S', 'requestActionCd': 'NEW'},
    {'nrTypeCd': 'XSO', 'entityTypeCd': 'XS', 'requestActionCd': 'NEW'},
    {'nrTypeCd': 'CP', 'entityTypeCd': 'CP', 'requestActionCd': 'NEW'},
    {'nrTypeCd': 'XCP', 'entityTypeCd': 'XCP', 'requestActionCd': 'NEW'},
    {'nrTypeCd': 'CC', 'entityTypeCd': 'CC', 'requestActionCd': 'NEW'},
    {'nrTypeCd': 'UL', 'entityTypeCd': 'ULC', 'requestActionCd': 'NEW'},
    # {'nrTypeCd': 'XUL', 'entityTypeCd': 'XUL', 'requestActionCd': 'NEW'},
    {'nrTypeCd': 'FI', 'entityTypeCd': 'FI', 'requestActionCd': 'NEW'},
    {'nrTypeCd': 'PA', 'entityTypeCd': 'PA', 'requestActionCd': 'NEW'},
    {'nrTypeCd': 'PAR', 'entityTypeCd': 'PAR', 'requestActionCd': 'NEW'},
    {'nrTypeCd': 'BC', 'entityTypeCd': 'BEN', 'requestActionCd': 'NEW'}
]

CR_BC_NEW_RESULTS = [
    {'nrTypeCd': 'CR', 'entityTypeCd': 'BC', 'requestActionCd': 'NEW'}
]


@pytest.mark.parametrize('params, results, num_results', [
    ('', None, 92),  # no parameters (all results)
    ('?nrTypeCd=CR', CR_RESULTS, None),  # NR Type Code "CR" only
    ('?entityTypeCd=BC', BC_RESULTS, None),  # Entity Type Code "BC" only
    ('?requestActionCd=NEW', NEW_RESULTS, None),  # Request Action Code "NEW" only
    ('?nrTypeCd=CR&entityTypeCd=BC&requestActionCd=NEW', CR_BC_NEW_RESULTS, None),  # all 3 parameters
    ('?nrTypeCd=INVALID', None, 0)  # invalid parameter
])
def test_various_parameters(client, params, results, num_results):
    """Assert that the endpoint returns the expected responses for various parameters."""
    from legal_api.version import __version__
    from registry_schemas import __version__ as registry_schemas_version

    rv = client.get('/api/v1/nrTypeMap' + params)

    if results:
        # function to sort JSON items
        def sortFunction(value):
            return value['nrTypeCd'] + value['entityTypeCd'] + value['requestActionCd']

        assert rv.status_code == 200
        assert sorted(rv.json, key=sortFunction) == sorted(results, key=sortFunction)

    elif num_results > 0:
        assert rv.status_code == 200
        assert len(rv.json) == num_results

    else:
        assert rv.status_code == 404
