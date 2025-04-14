# Copyright © 2022 Province of British Columbia
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
"""File processing rules and actions for the registration of a business."""
import copy
from typing import Dict

from business_filer.exceptions import QueueException
from business_model.models import Business, Filing
from business_filer.services import Flags
from business_filer.common.legislation_datetime import LegislationDatetime

from business_filer.filing_meta import FilingMeta
from business_filer.filing_processors.filing_components import business_info, filings
from business_filer.filing_processors.filing_components.offices import update_offices
from business_filer.filing_processors.filing_components.parties import update_parties


def process(business: Business,  # pylint: disable=too-many-branches
            filing: Dict,
            filing_rec: Filing,
            filing_meta: FilingMeta,
            flags: Flags):  # pylint: disable=too-many-branches
    """Process the incoming registration filing."""
    # Extract the filing information for registration
    registration_filing = filing.get('filing', {}).get('registration')
    filing_meta.registration = {}

    if not registration_filing:
        raise QueueException(f'Registration legal_filing:registration missing from {filing_rec.id}')
    if business:
        raise QueueException(f'Business Already Exist: Registration legal_filing:registration {filing_rec.id}')

    business_info_obj = registration_filing.get('nameRequest')

    # Reserve the Corp Number for this entity
    corp_num = business_info.get_next_corp_num('FM', flags)
    if not corp_num:
        raise QueueException(
            f'registration {filing_rec.id} unable to get a business registration number.')

    # Initial insert of the business record
    business = Business()
    business = business_info.update_business_info(corp_num, business, business_info_obj, filing_rec)
    business.start_date = \
        LegislationDatetime.as_utc_timezone_from_legislation_date_str(registration_filing.get('startDate'))

    business_obj = registration_filing.get('business', {})
    if (naics := business_obj.get('naics')) and naics.get('naicsCode'):
        business_info.update_naics_info(business, naics)
    business.tax_id = business_obj.get('taxId', None)
    business.state = Business.State.ACTIVE

    if nr_number := business_info_obj.get('nrNumber', None):
        filing_meta.registration = {**filing_meta.registration,
                                    **{'nrNumber': nr_number,
                                       'legalName': business_info_obj.get('legalName', None)}}

    if not business:
        raise QueueException(f'Registration {filing_rec.id}, Unable to create business.')

    if offices := registration_filing['offices']:
        update_offices(business, offices)

    if parties := registration_filing.get('parties'):
        update_parties(business, parties, filing_rec)

    # update court order, if any is present
    if court_order := registration_filing.get('courtOrder'):
        filings.update_filing_court_order(filing_rec, court_order)

    # Update the filing json with identifier and founding date.
    registration_json = copy.deepcopy(filing_rec.filing_json)
    registration_json['filing']['business'] = {}
    registration_json['filing']['business']['identifier'] = business.identifier
    registration_json['filing']['registration']['business']['identifier'] = business.identifier
    registration_json['filing']['business']['legalType'] = business.legal_type
    registration_json['filing']['business']['foundingDate'] = business.founding_date.isoformat()
    filing_rec._filing_json = registration_json  # pylint: disable=protected-access; bypass to update filing data

    return business, filing_rec, filing_meta
