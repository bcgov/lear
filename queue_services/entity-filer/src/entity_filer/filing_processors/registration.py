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
from contextlib import suppress
from datetime import timedelta
from http import HTTPStatus
from typing import Dict

import dpath
import sentry_sdk
from entity_queue_common.service_utils import QueueException
from legal_api.models import Business, Filing, RegistrationBootstrap
from legal_api.services.bootstrap import AccountService
from legal_api.utils.datetime import datetime

from entity_filer.filing_meta import FilingMeta
from entity_filer.filing_processors.filing_components import business_info, business_profile, filings
from entity_filer.filing_processors.filing_components.offices import update_offices
from entity_filer.filing_processors.filing_components.parties import update_parties


def update_affiliation(business: Business, filing: Filing):
    """Create an affiliation for the business and remove the bootstrap."""
    try:
        bootstrap = RegistrationBootstrap.find_by_identifier(filing.temp_reg)
        pass_code = business_info.get_firm_affiliation_passcode(business.id)

        nr_number = filing.filing_json.get('filing').get('registration', {}).get('nameRequest', {}).get('nrNumber')
        details = {
            'bootstrapIdentifier': bootstrap.identifier,
            'identifier': business.identifier,
            'nrNumber': nr_number
        }

        rv = AccountService.create_affiliation(
            account=bootstrap.account,
            business_registration=business.identifier,
            business_name=business.legal_name,
            corp_type_code=business.legal_type,
            pass_code=pass_code,
            details=details
        )

        if rv not in (HTTPStatus.OK, HTTPStatus.CREATED):
            deaffiliation = AccountService.delete_affiliation(bootstrap.account, business.identifier)
            sentry_sdk.capture_message(
                f'Queue Error: Unable to affiliate business:{business.identifier} for filing:{filing.id}',
                level='error'
            )
        else:
            # flip the registration
            # recreate the bootstrap, but point to the new business in the name
            old_bs_affiliation = AccountService.delete_affiliation(bootstrap.account, bootstrap.identifier)
            new_bs_affiliation = AccountService.create_affiliation(
                account=bootstrap.account,
                business_registration=bootstrap.identifier,
                business_name=business.identifier,
                corp_type_code='RTMP'
            )
            reaffiliate = bool(new_bs_affiliation in (HTTPStatus.OK, HTTPStatus.CREATED)
                               and old_bs_affiliation == HTTPStatus.OK)

        if rv not in (HTTPStatus.OK, HTTPStatus.CREATED) \
                or ('deaffiliation' in locals() and deaffiliation != HTTPStatus.OK)\
                or ('reaffiliate' in locals() and not reaffiliate):
            raise QueueException
    except Exception as err:  # pylint: disable=broad-except; note out any exception, but don't fail the call
        sentry_sdk.capture_message(
            f'Queue Error: Affiliation error for filing:{filing.id}, with err:{err}',
            level='error'
        )


def process(business: Business,  # pylint: disable=too-many-branches
            filing: Dict,
            filing_rec: Filing,
            filing_meta: FilingMeta):  # pylint: disable=too-many-branches
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
    corp_num = business_info.get_next_corp_num('FM')
    if not corp_num:
        raise QueueException(
            f'registration {filing_rec.id} unable to get a business registration number.')

    # Initial insert of the business record
    business = Business()
    business = business_info.update_business_info(corp_num, business, business_info_obj, filing_rec)
    business.start_date = datetime.fromisoformat(registration_filing.get('startDate')) + timedelta(hours=8)
    business.founding_date = filing_rec.effective_date

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
    with suppress(IndexError, KeyError, TypeError):
        court_order_json = dpath.util.get(filing, '/registration/courtOrder')
        filings.update_filing_court_order(filing_rec, court_order_json)

    # Update the filing json with identifier and founding date.
    registration_json = copy.deepcopy(filing_rec.filing_json)
    registration_json['filing']['business'] = {}
    registration_json['filing']['business']['identifier'] = business.identifier
    registration_json['filing']['registration']['business']['identifier'] = business.identifier
    registration_json['filing']['business']['legalType'] = business.legal_type
    registration_json['filing']['business']['foundingDate'] = business.founding_date.isoformat()
    filing_rec._filing_json = registration_json  # pylint: disable=protected-access; bypass to update filing data

    return business, filing_rec, filing_meta


def post_process(business: Business, filing: Filing):
    """Post processing activities for registration.

    THIS SHOULD NOT ALTER THE MODEL
    """
    with suppress(IndexError, KeyError, TypeError):
        if err := business_profile.update_business_profile(
            business,
            filing.json['filing']['registration']['contactPoint']
        ):
            sentry_sdk.capture_message(
                f'Queue Error: Update Business for filing:{filing.id}, error:{err}',
                level='error')
