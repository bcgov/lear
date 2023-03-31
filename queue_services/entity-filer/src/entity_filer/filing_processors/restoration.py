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
from datetime import timedelta
from typing import Dict

import dpath
import sentry_sdk
from legal_api.models import Business, Filing, PartyRole
from legal_api.utils.datetime import datetime

from entity_filer.filing_meta import FilingMeta
from entity_filer.filing_processors.filing_components import aliases, business_info, business_profile, filings, name_request
from entity_filer.filing_processors.filing_components.offices import update_offices
from entity_filer.filing_processors.filing_components.parties import update_parties


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
        business.restoration_expiry_date = datetime.fromisoformat(expiry) + timedelta(hours=8)
        filing_meta.restoration = {
            **filing_meta.restoration,
            'expiry': expiry
        }
    else:  # fullRestoration, limitedRestorationToFull
        business.restoration_expiry_date = None

    business.state = Business.State.ACTIVE
    business.dissolution_date = None
    business.state_filing_id = filing_rec.id

    update_offices(business, restoration_filing['offices'])

    if name_translations := restoration_filing.get('nameTranslations'):
        aliases.update_aliases(business, name_translations)

    parties = restoration_filing['parties']
    _update_parties(business, parties, filing_rec)

    filing_rec.approval_type = restoration_filing.get('approvalType')
    if filing_rec.approval_type == 'courtOrder':
        with suppress(IndexError, KeyError, TypeError):
            court_order_json = dpath.util.get(restoration_filing, '/courtOrder')
            filings.update_filing_court_order(filing_rec, court_order_json)
    elif filing_rec.approval_type == 'registrar':
        application_date = restoration_filing.get('applicateDate')
        notice_date = restoration_filing.get('noticeDate')
        if application_date and notice_date:
            application_date_formatted = datetime.fromisoformat(application_date) + timedelta(hours=8)
            notice_date_formatted = datetime.fromisoformat(notice_date) + timedelta(hours=8)
            filing_rec.applicate_date = application_date_formatted #wait for argus
            filing_rec.notice_date = notice_date_formatted #wait for argus

def _update_parties(business: Business, parties: dict, filing_rec: Filing):
    """Create applicant party and cease custodian if exist."""
    end_date_time = datetime.utcnow()
    custodian_party_roles = PartyRole.get_party_roles(business.id, end_date_time.date(),
                                                      PartyRole.RoleTypes.CUSTODIAN.value)
    for party_role in custodian_party_roles:
        party_role.cessation_date = end_date_time
        business.party_roles.append(party_role)

    update_parties(business, parties, filing_rec, False)


def post_process(business: Business, filing: Filing):
    """Post processing activities for restoration.

    THIS SHOULD NOT ALTER THE MODEL
    """
    name_request.consume_nr(business, filing, 'restoration')

    with suppress(IndexError, KeyError, TypeError):
        if err := business_profile.update_business_profile(
            business,
            filing.json['filing']['restoration']['contactPoint']
        ):
            sentry_sdk.capture_message(
                f'Queue Error: Update Business for filing:{filing.id},error:{err}',
                level='error')
