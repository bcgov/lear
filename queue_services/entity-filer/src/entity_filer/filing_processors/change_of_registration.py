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
"""File processing rules and actions for the change of registration filing."""
import datetime
from contextlib import suppress
from typing import Dict

import dpath
from business_model import Address, AlternateName, BusinessCommon, Filing, LegalEntity, db

from entity_filer.exceptions.default_exception import DefaultException
from entity_filer.filing_meta import FilingMeta
from entity_filer.filing_processors.filing_components import filings, legal_entity_info, name_request, update_address
from entity_filer.filing_processors.filing_components.alternate_name import (
    update_partner_change,
    update_proprietor_change,
)
from entity_filer.filing_processors.filing_components.parties import get_or_create_party, merge_all_parties
from entity_filer.filing_processors.registration import get_partnership_name


def process(
    business: any,
    change_filing_rec: Filing,
    change_filing: Dict,
    filing_meta: FilingMeta,
):
    """Render the change of registration filing onto the business model objects."""
    filing_meta.change_of_registration = {}
    match business.entity_type:
        case BusinessCommon.EntityTypes.PARTNERSHIP:
            business, alternate_name = update_partner_change(
                legal_entity=business,
                filing_type="changeOfRegistration",
                change_filing_rec=change_filing_rec,
                change_filing=change_filing,
                filing_meta=filing_meta.change_of_registration,
            )
        case BusinessCommon.EntityTypes.SOLE_PROP:
            business, alternate_name = update_proprietor_change(
                filing_type="changeOfRegistration",
                change_filing_rec=change_filing_rec,
                change_filing=change_filing,
                filing_meta=filing_meta.change_of_registration,
            )
        case _:
            # Default and failed
            raise DefaultException(f"change of registration {change_filing_rec.id} had no valid Firm type.")

    # Update business office if present
    with suppress(IndexError, KeyError, TypeError):
        business_office_json = dpath.util.get(change_filing, "/changeOfRegistration/offices/businessOffice")
        for updated_address in business_office_json.values():
            if updated_address.get("id", None):
                address = Address.find_by_id(updated_address.get("id"))
                if address:
                    update_address(address, updated_address)

    # Update parties
    with suppress(IndexError, KeyError, TypeError):
        parties = dpath.util.get(change_filing, "/changeOfRegistration/parties")
        merge_all_parties(business, change_filing_rec, {"parties": parties})

    # update court order, if any is present
    with suppress(IndexError, KeyError, TypeError):
        court_order_json = dpath.util.get(change_filing, "/changeOfRegistration/courtOrder")
        filings.update_filing_court_order(change_filing_rec, court_order_json)

    return business, alternate_name


def post_process(business: LegalEntity, filing: Filing):
    """Post processing activities for change of registration.

    THIS SHOULD NOT ALTER THE MODEL
    """
    name_request.consume_nr(business, filing, "changeOfRegistration")
