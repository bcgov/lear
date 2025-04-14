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
import datetime

from business_model.models import Filing
from registry_schemas.example_data import TRANSITION_FILING_TEMPLATE

from business_filer.filing_meta import FilingMeta
from business_filer.filing_processors import transition
from tests.unit import create_business, create_filing


def test_transition_filing_process(app, session):
    """Assert that the transition object is correctly populated to model objects."""
    # setup
    filing = copy.deepcopy(TRANSITION_FILING_TEMPLATE)

    business = create_business(filing['filing']['business']['identifier'])
    create_filing('123', filing)

    effective_date = datetime.datetime.utcnow()
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
