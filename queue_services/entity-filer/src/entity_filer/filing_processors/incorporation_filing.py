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
"""File processing rules and actions for the incorporation of a business."""
import copy
from contextlib import suppress
from http import HTTPStatus
from typing import Dict

import requests
import sentry_sdk
from entity_queue_common.service_utils import QueueException
from flask import current_app
from legal_api.models import Business, Filing, RegistrationBootstrap
from legal_api.services.bootstrap import AccountService

from entity_filer.filing_processors.filing_components import aliases, business_info, business_profile, shares
from entity_filer.filing_processors.filing_components.offices import update_offices
from entity_filer.filing_processors.filing_components.parties import update_parties


def get_next_corp_num(business_type: str):
    """Retrieve the next available sequential corp-num from COLIN."""
    try:
        resp = requests.post(f'{current_app.config["COLIN_API"]}/{business_type}')
    except requests.exceptions.ConnectionError:
        current_app.logger.error(f'Failed to connect to {current_app.config["COLIN_API"]}')
        return None

    if resp.status_code == 200:
        new_corpnum = int(resp.json()['corpNum'])
        if new_corpnum and new_corpnum <= 9999999:
            # TODO: Fix endpoint
            return f'{business_type}{new_corpnum:07d}'
    return None


def update_affiliation(business: Business, filing: Filing):
    """Create an affiliation for the business and remove the bootstrap."""
    try:
        bootstrap = RegistrationBootstrap.find_by_identifier(filing.temp_reg)

        rv = AccountService.create_affiliation(
            account=bootstrap.account,
            business_registration=business.identifier,
            business_name=business.legal_name,
            corp_type_code=business.legal_type
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
                corp_type_code='TMP'
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


def process(business: Business, filing: Dict, filing_rec: Filing):
    # pylint: disable=too-many-locals; 1 extra
    """Process the incoming incorporation filing."""
    # Extract the filing information for incorporation
    incorp_filing = filing.get('incorporationApplication')
    is_correction = filing.get('correction', None)

    if not incorp_filing:
        raise QueueException(f'IA legal_filing:incorporationApplication missing from {filing_rec.id}')
    if business and not is_correction:
        raise QueueException(f'Business Already Exist: IA legal_filing:incorporationApplication {filing_rec.id}')

    business_info_obj = incorp_filing.get('nameRequest')

    if is_correction:
        business_info.set_legal_name(business.identifier, business, business_info_obj)
    else:
        # Reserve the Corp Number for this entity
        corp_num = get_next_corp_num(business_info_obj['legalType'])
        if not corp_num:
            raise QueueException(
                f'incorporationApplication {filing_rec.id} unable to get a business registration number.')
        # Initial insert of the business record
        business = Business()
        business = business_info.update_business_info(corp_num, business, business_info_obj, filing_rec)
        if not business:
            raise QueueException(f'IA incorporationApplication {filing_rec.id}, Unable to create business.')

    if offices := incorp_filing['offices']:
        update_offices(business, offices)

    if parties := incorp_filing.get('parties'):
        update_parties(business, parties)

    if share_structure := incorp_filing['shareStructure']:
        shares.update_share_structure(business, share_structure)

    if name_translations := incorp_filing.get('nameTranslations'):
        aliases.update_aliases(business, name_translations)

    if not is_correction:
        # Update the filing json with identifier and founding date.
        ia_json = copy.deepcopy(filing_rec.filing_json)
        ia_json['filing']['business']['identifier'] = business.identifier
        ia_json['filing']['business']['foundingDate'] = business.founding_date.isoformat()
        filing_rec._filing_json = ia_json  # pylint: disable=protected-access; bypass to update filing data
    return business, filing_rec


def post_process(business: Business, filing: Filing):
    """Post processing activities for incorporations.

    THIS SHOULD NOT ALTER THE MODEL
    """
    with suppress(IndexError, KeyError, TypeError):
        if err := business_profile.update_business_profile(
            business,
            filing.json['filing']['incorporationApplication']['contactPoint']
        ):
            sentry_sdk.capture_message(
                f'Queue Error: Update Business for filing:{filing.id}, error:{err}',
                level='error')
