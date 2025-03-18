# Copyright © 2025 Province of British Columbia
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

"""The Test-Suite used to ensure that the Model objects are working correctly."""
import base64
import uuid

from datedelta import datedelta
from freezegun import freeze_time

from business_model.models import (
  Address,
  Business,
  db
)

from tests import EPOCH_DATETIME, FROZEN_DATETIME


def factory_user(username: str, firstname: str = None, lastname: str = None):
    user = User()
    user.username = username
    user.firstname = firstname
    user.lastname = lastname
    user.save()
    return user


def factory_business(identifier,
                     founding_date=EPOCH_DATETIME,
                     last_ar_date=None,
                     entity_type=Business.LegalTypes.COOP.value,
                     state=Business.State.ACTIVE,
                     naics_code=None,
                     naics_desc=None,
                     admin_freeze=False,
                     no_dissolution=False):
    """Create a business entity with a versioned business."""
    last_ar_year = None
    if last_ar_date:
        last_ar_year = last_ar_date.year
    business = Business(legal_name=f'legal_name-{identifier}',
                        founding_date=founding_date,
                        last_ar_date=last_ar_date,
                        last_ar_year=last_ar_year,
                        last_ledger_timestamp=EPOCH_DATETIME,
                        # dissolution_date=EPOCH_DATETIME,
                        identifier=identifier,
                        tax_id='BN123456789',
                        fiscal_year_end_date=FROZEN_DATETIME,
                        legal_type=entity_type,
                        state=state,
                        naics_code=naics_code,
                        naics_description=naics_desc,
                        admin_freeze=admin_freeze,
                        no_dissolution=no_dissolution)

    business.save()
    return business
