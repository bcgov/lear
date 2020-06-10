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
from http import HTTPStatus
from typing import Dict

import requests
import sentry_sdk
from entity_queue_common.service_utils import QueueException
from flask import current_app
from legal_api.models import Business, Filing, RegistrationBootstrap
from legal_api.services.bootstrap import AccountService

from entity_filer.filing_processors import create_office, create_party, create_role, create_share_class


def get_next_corp_num(business_type: str):
    """Retrieve the next available sequential corp-num from COLIN."""
    try:
        resp = requests.get(f'{current_app.config["COLIN_API"]}?legal_type={business_type}')
    except requests.exceptions.ConnectionError:
        current_app.logger.error(f'Failed to connect to {current_app.config["COLIN_API"]}')
        return None

    if resp.status_code == 200:
        new_corpnum = resp.json()['corpNum'][0]
        if new_corpnum and new_corpnum <= 9999999:
            # TODO: Fix endpoint
            return f'{business_type}{new_corpnum:07d}'
    return None


def update_business_info(corp_num: str, business: Business, business_info: Dict, filing: Dict, filing_rec: Filing):
    """Format and update the business entity from incorporation filing."""
    if corp_num and business and business_info and filing and filing_rec:
        legal_name = business_info.get('legalName', None)
        business.identifier = corp_num
        business.legal_name = legal_name if legal_name else corp_num[2:] + ' B.C. LTD.'
        business.legal_type = business_info.get('legalType', None)
        business.founding_date = filing_rec.effective_date
        return business
    return None


def update_affiliation(business: Business, filing: Filing):
    """Create an affiliation for the business and remove the bootstrap."""
    try:
        bootstrap = RegistrationBootstrap.find_by_identifier(filing.temp_reg)

        rv = AccountService.create_affiliation(
            account=bootstrap.account,
            business_registration=business.identifier,
            business_name=business.legal_name
        )

        if rv in (HTTPStatus.OK, HTTPStatus.CREATED):
            deaffiliation = AccountService.delete_affiliation(bootstrap.account, business.identifier)

        if rv not in (HTTPStatus.OK, HTTPStatus.CREATED) \
                or ('deaffiliation' in locals() and deaffiliation != HTTPStatus.OK):
            raise QueueException
    except Exception:  # pylint: disable=broad-except; note out any exception, but don't fail the call
        sentry_sdk.capture_message(f'Queue Error: Affiliation error for filing:{filing.id}', level='error')


def process(business: Business, filing: Dict, filing_rec: Filing):
    # pylint: disable=too-many-locals; 1 extra
    """Process the incoming incorporation filing."""
    # Extract the filing information for incorporation
    incorp_filing = filing.get('incorporationApplication')

    if not incorp_filing:
        raise QueueException(f'IA legal_filing:incorporationApplication missing from {filing_rec.id}')
    if business:
        raise QueueException(f'Business Already Exist: IA legal_filing:incorporationApplication {filing_rec.id}')

    offices = incorp_filing.get('offices', None)
    parties = incorp_filing.get('parties', None)
    business_info = incorp_filing.get('nameRequest')
    share_classes = incorp_filing['shareClasses']

    # Reserve the Corp Numper for this entity
    corp_num = get_next_corp_num(business_info['legalType'])
    if not corp_num:
        raise QueueException(f'incorporationApplication {filing_rec.id} unable to get a business registration number.')

    # Initial insert of the business record
    business = Business()
    business = update_business_info(corp_num, business, business_info, incorp_filing, filing_rec)
    if not business:
        raise QueueException(f'IA incorporationApplication {filing_rec.id}, Unable to create business.')

    for office_type, addresses in offices.items():
        office = create_office(business, office_type, addresses)
        business.offices.append(office)

    if parties:
        for party_info in parties:
            party = create_party(business_id=business.id, party_info=party_info)
            for role_type in party_info.get('roles'):
                role = {
                    'roleType': role_type.get('roleType'),
                    'appointmentDate': role_type.get('appointmentDate', None),
                    'cessationDate': role_type.get('cessationDate', None)
                }
                party_role = create_role(party=party, role_info=role)
                business.party_roles.append(party_role)

    if share_classes:
        for share_class_info in share_classes:
            share_class = create_share_class(share_class_info)
            business.share_classes.append(share_class)

    ia_json = copy.deepcopy(filing_rec.filing_json)
    ia_json['filing']['business']['identifier'] = business.identifier
    ia_json['filing']['business']['foundingDate'] = business.founding_date.isoformat()
    filing_rec._filing_json = ia_json  # pylint: disable=protected-access; bypass to update filing data
    return business, filing_rec
