# Copyright © 2023 Province of British Columbia
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
"""File processing rules and actions for the restoration on filing."""

from contextlib import suppress
from typing import Dict

import dpath
from business_model.models import Business, Filing, PartyRole
from business_filer.common.datetime import datetime
from business_filer.common.legislation_datetime import LegislationDatetime

from business_filer.filing_meta import FilingMeta
from business_filer.filing_processors.filing_components import business_info, filings
from business_filer.filing_processors.filing_components.aliases import update_aliases
from business_filer.filing_processors.filing_components.offices import update_offices
from business_filer.filing_processors.filing_components.parties import update_parties


def process(business: Business, filing: Dict, filing_rec: Filing, filing_meta: FilingMeta):
    """Process restoration filing."""
    restoration_filing = filing.get('restoration')
    filing_meta.restoration = {}

    from_legal_name = business.legal_name

    if name_request_json := restoration_filing.get('nameRequest'):
        business_info.set_legal_name(business.identifier, business, name_request_json)
        if nr_number := name_request_json.get('nrNumber', None):
            filing_meta.restoration = {
                **filing_meta.restoration,
                'nrNumber': nr_number
            }

    filing_meta.restoration = {
        **filing_meta.restoration,
        'fromLegalName': from_legal_name,
        'toLegalName': business.legal_name
        # if restoration is from a numbered to numbered, fromLegalName and toLegalName will be same
        # adding this intentionally for now to refer in ledger (filing-ui)
    }

    if expiry := restoration_filing.get('expiry'):  # limitedRestoration, limitedRestorationExtension
        business.restoration_expiry_date = LegislationDatetime.as_utc_timezone_from_legislation_date_str(expiry)
        filing_meta.restoration = {
            **filing_meta.restoration,
            'expiry': expiry
        }
    else:  # fullRestoration, limitedRestorationToFull
        business.restoration_expiry_date = None

    business.state = Business.State.ACTIVE
    business.dissolution_date = None
    business.state_filing_id = filing_rec.id

    if name_translations := restoration_filing.get('nameTranslations'):
        update_aliases(business, name_translations)

    update_offices(business, restoration_filing['offices'])

    cease_custodian(business)
    update_parties(business,
                   restoration_filing['parties'],
                   filing_rec,
                   False)

    filing_rec.approval_type = restoration_filing.get('approvalType')
    if filing_rec.approval_type == 'courtOrder':
        with suppress(IndexError, KeyError, TypeError):
            court_order_json = dpath.util.get(restoration_filing, '/courtOrder')
            filings.update_filing_court_order(filing_rec, court_order_json)
    elif filing_rec.approval_type == 'registrar':
        application_date = restoration_filing.get('applicationDate')
        notice_date = restoration_filing.get('noticeDate')
        if application_date and notice_date:
            filing_rec.application_date = \
                LegislationDatetime.as_utc_timezone_from_legislation_date_str(application_date)
            filing_rec.notice_date = LegislationDatetime.as_utc_timezone_from_legislation_date_str(notice_date)


def cease_custodian(business: Business):
    """Cease custodian if exist."""
    end_date_time = datetime.utcnow()
    custodian_party_roles = PartyRole.get_party_roles(business.id,
                                                      end_date_time.date(),
                                                      PartyRole.RoleTypes.CUSTODIAN.value)
    for party_role in custodian_party_roles:
        party_role.cessation_date = end_date_time
        business.party_roles.append(party_role)
