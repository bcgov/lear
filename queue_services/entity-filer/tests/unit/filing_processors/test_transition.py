# Copyright © 2020 Province of British Columbia
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
"""The Unit Tests for the Transition filing."""

import copy
from datetime import datetime

from legal_api.models import Filing
from registry_schemas.example_data import TRANSITION_FILING_TEMPLATE

from entity_filer.filing_processors import transition
from tests.unit import create_filing


def test_transition_filing_process(app, session):
    """Assert that the transition object is correctly populated to model objects."""
    # setup
    filing = copy.deepcopy(TRANSITION_FILING_TEMPLATE)
    create_filing('123', filing)

    effective_date = datetime.utcnow()
    filing_rec = Filing(effective_date=effective_date, filing_json=filing)
    print(filing_rec.filing_json)

    # test
    business, filing_rec = transition.process(None, filing['filing'], filing_rec)

    # Assertions
    assert business.identifier == filing['filing']['business']['identifier']
    assert business.founding_date == effective_date
    assert business.legal_type == filing['filing']['business']['legalType']
    assert business.legal_name == filing['filing']['business']['legalName']
    assert business.restriction_ind is False
    assert len(business.share_classes.all()) == 2
    assert len(business.offices.all()) == 2  # One office is created in create_business method.
    assert len(business.aliases.all()) == 3
    assert len(business.resolutions.all()) == 2
    assert len(business.party_roles.all()) == 2
