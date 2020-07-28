# Copyright © 2019 Province of British Columbia
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
"""The Unit Tests for the business filing component processors."""
from legal_api.models import Business

from entity_filer.filing_processors.filing_components import business


def test_set_corp_type(app, session):
    new_info_json = {
        'business': {
            'corpType': 'benefitCompany'
        }}

    business = Business()
    business, err = business.set_corp_type(business, new_info_json)
