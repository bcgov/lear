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
"""Validation for the Incorporation filing."""
from datetime import timedelta
from http import HTTPStatus  # pylint: disable=wrong-import-order
from typing import Final

import pycountry
from flask_babel import _ as babel  # noqa: N813, I004, I001, I003

from legal_api.core.filing import Filing as coreFiling  # noqa: I001
from legal_api.errors import Error
from legal_api.models import Business
from legal_api.services.utils import get_str
from legal_api.utils.datetime import datetime as dt
from legal_api.constants import DocumentClasses

from .common_validations import (  # noqa: I001
    validate_court_order,
    validate_name_request,
    validate_parties_names,
    validate_pdf,
    validate_share_structure,
)


def validate(incorporation_json: dict):  # pylint: disable=too-many-branches;
    """Validate the Incorporation filing."""
    filing_type = 'incorporationApplication'
    if not incorporation_json:
        return Error(HTTPStatus.BAD_REQUEST, [{'error': babel('A valid filing is required.')}])
    msg = []

    legal_type_path = '/filing/incorporationApplication/nameRequest/legalType'
    legal_type = get_str(incorporation_json, legal_type_path)
    if not legal_type:
        msg.append({'error': babel('Legal type is required.'), 'path': legal_type_path})
        return msg  # Cannot continue validation without legal_type

    msg.extend(validate_offices(incorporation_json))

    err = validate_roles(incorporation_json, legal_type)
    if err:
        msg.extend(err)

    msg.extend(validate_parties_names(incorporation_json, filing_type))

    err = validate_parties_mailing_address(incorporation_json, legal_type)
    if err:
        msg.extend(err)

    msg.extend(validate_name_request(incorporation_json, legal_type, filing_type))

    if legal_type in [Business.LegalTypes.BCOMP.value, Business.LegalTypes.BC_ULC_COMPANY.value,
                      Business.LegalTypes.COMP.value, Business.LegalTypes.BC_CCC.value]:
        err = validate_share_structure(incorporation_json, coreFiling.FilingTypes.INCORPORATIONAPPLICATION.value)
        if err:
            msg.extend(err)

    elif legal_type == Business.LegalTypes.COOP.value:
        msg.extend(validate_cooperative_documents(incorporation_json))

    err = validate_incorporation_effective_date(incorporation_json)
    if err:
        msg.extend(err)

    msg.extend(validate_ia_court_order(incorporation_json))

    if msg:
        return Error(HTTPStatus.BAD_REQUEST, msg)
    return None


def validate_offices(filing_json: dict, filing_type: str = 'incorporationApplication') -> list:
    """Validate the office addresses of the specified corp filing type."""
    offices_array = filing_json['filing'][filing_type]['offices']
    addresses = offices_array
    msg = []

    for item in addresses.keys():
        if item in ('registeredOffice', 'recordsOffice'):
            msg.extend(_validate_address(addresses, item, filing_type))
        else:
            msg.append({'error': f'Invalid office {item}. Only registeredOffice and recordsOffice are allowed.',
                        'path': f'/filing/{filing_type}/offices'})

    return msg


def _validate_address(addresses: dict, address_key: str, filing_type: str) -> list:
    """Validate the addresses of the specified corp filing type."""
    msg = []

    for k, v in addresses[address_key].items():
        region = v.get('addressRegion')
        country = v['addressCountry']

        if region != 'BC':
            path = f'/filing/{filing_type}/offices/%s/%s/addressRegion' % (
                address_key, k
            )
            msg.append({'error': "Address Region must be 'BC'.",
                        'path': path})

        try:
            country = pycountry.countries.search_fuzzy(country)[0].alpha_2
            if country != 'CA':
                raise LookupError
        except LookupError:
            err_path = f'/filing/{filing_type}/offices/%s/%s/addressCountry' % (
                address_key, k
            )
            msg.append({'error': "Address Country must be 'CA'.",
                        'path': err_path})

    return msg


# pylint: disable=too-many-branches
def validate_roles(filing_dict: dict, legal_type: str, filing_type: str = 'incorporationApplication') -> Error:
    """Validate the required completing party of the incorporation filing."""
    min_director_count_info = {
        Business.LegalTypes.BCOMP.value: 1,
        Business.LegalTypes.COMP.value: 1,
        Business.LegalTypes.BC_ULC_COMPANY.value: 1,
        Business.LegalTypes.BC_CCC.value: 3,
        Business.LegalTypes.BCOMP_CONTINUE_IN.value: 1,
        Business.LegalTypes.CONTINUE_IN.value: 1,
        Business.LegalTypes.ULC_CONTINUE_IN.value: 1,
        Business.LegalTypes.CCC_CONTINUE_IN.value: 3
    }
    parties_array = filing_dict['filing'][filing_type]['parties']
    msg = []
    completing_party_count = 0
    incorporator_count = 0
    director_count = 0

    for item in parties_array:
        for role in item['roles']:
            if role['roleType'] == 'Completing Party':
                completing_party_count += 1

            if role['roleType'] == 'Incorporator':
                incorporator_count += 1

            if role['roleType'] == 'Director':
                director_count += 1

    if filing_type == 'incorporationApplication' or \
            (filing_type == 'correction' and filing_dict['filing'][filing_type].get('type') == 'CLIENT'):
        if completing_party_count == 0:
            err_path = f'/filing/{filing_type}/parties/roles'
            msg.append({'error': 'Must have a minimum of one completing party', 'path': err_path})
        elif completing_party_count > 1:
            err_path = f'/filing/{filing_type}/parties/roles'
            msg.append({'error': 'Must have a maximum of one completing party', 'path': err_path})
    elif filing_type == 'correction' and filing_dict['filing'][filing_type].get('type') == 'STAFF' and \
            completing_party_count != 0:
        err_path = f'/filing/{filing_type}/parties/roles'
        msg.append({'error': 'Should not provide completing party when correction type is STAFF', 'path': err_path})

    if legal_type == Business.LegalTypes.COOP.value:
        if incorporator_count > 0:
            err_path = f'/filing/{filing_type}/parties/roles'
            msg.append({'error': 'Incorporator is an invalid party role', 'path': err_path})

        if director_count < 3:
            err_path = f'/filing/{filing_type}/parties/roles'
            msg.append({'error': 'Must have a minimum of three Directors', 'path': err_path})
    else:
        # FUTURE: THis may have to be altered based on entity type in the future
        min_director_count = min_director_count_info.get(legal_type, 0)
        if filing_type == 'incorporationApplication' and incorporator_count < 1:
            err_path = f'/filing/{filing_type}/parties/roles'
            msg.append({'error': 'Must have a minimum of one Incorporator', 'path': err_path})
        elif filing_type == 'correction' and incorporator_count > 0:
            err_path = f'/filing/{filing_type}/parties/roles'
            msg.append({'error': 'Cannot correct Incorporator role', 'path': err_path})

        if director_count < min_director_count:
            err_path = f'/filing/{filing_type}/parties/roles'
            msg.append({'error': f'Must have a minimum of {min_director_count} Director', 'path': err_path})

    if msg:
        return msg

    return None


def validate_parties_mailing_address(incorporation_json: dict, legal_type: str,
                                     filing_type: str = 'incorporationApplication') -> Error:
    """Validate the person data of the incorporation filing."""
    parties_array = incorporation_json['filing'][filing_type]['parties']
    msg = []
    bc_party_ma_count = 0
    country_ca_party_ma_count = 0
    country_total_ma_count = 0

    for item in parties_array:
        for k, v in item['mailingAddress'].items():
            if v is None:
                err_path = f'/filing/{filing_type}/parties/%s/mailingAddress/%s/%s/' % (
                    item['officer']['id'], k, v
                )
                msg.append({'error': 'Person %s: Mailing address %s %s is invalid' % (
                    item['officer']['id'], k, v
                ), 'path': err_path})

            if (ma_region := item.get('mailingAddress', {}).get('addressRegion', None)) and ma_region == 'BC':
                bc_party_ma_count += 1

            if (ma_country := item.get('mailingAddress', {}).get('addressCountry', None)):
                country_total_ma_count += 1
                if ma_country == 'CA':
                    country_ca_party_ma_count += 1

    if legal_type == Business.LegalTypes.COOP.value:
        if bc_party_ma_count < 1:
            err_path = f'/filing/{filing_type}/parties/mailingAddress'
            msg.append({'error': 'Must have minimum of one BC mailing address', 'path': err_path})

        country_ca_percentage = country_ca_party_ma_count / country_total_ma_count * 100
        if country_ca_percentage <= 50:
            err_path = f'/filing/{filing_type}/parties/mailingAddress'
            msg.append({'error': 'Must have majority of mailing addresses in Canada', 'path': err_path})

    if msg:
        return msg

    return None


def validate_incorporation_effective_date(incorporation_json: dict) -> Error:
    """Return an error or warning message based on the effective date validation rules.

    Rules:
        - The effective date must be the correct format.
        - The effective date must be a minimum of 2 minutes in the future.
        - The effective date must be a maximum of 10 days in the future.
    """
    # Setup
    msg = []
    now = dt.utcnow()
    now_plus_2_minutes = now + timedelta(minutes=2)
    now_plus_10_days = now + timedelta(days=10)

    try:
        filing_effective_date = incorporation_json['filing']['header']['effectiveDate']
    except KeyError:
        return msg

    try:
        effective_date = dt.fromisoformat(filing_effective_date)
    except ValueError:
        msg.append({'error': babel('%s is an invalid ISO format for effective_date.') % filing_effective_date})
        return msg

    if effective_date < now_plus_2_minutes:
        msg.append({'error': babel('Invalid Datetime, effective date must be a minimum of 2 minutes ahead.')})

    if effective_date > now_plus_10_days:
        msg.append({'error': babel('Invalid Datetime, effective date must be a maximum of 10 days ahead.')})

    if msg:
        return msg

    return None


def validate_cooperative_documents(incorporation_json: dict):
    """Return an error or warning message based on the cooperative documents validation rules.

    Rules:
        - The documents are provided.
        - Document IDs are unique.
    """
    if not (cooperative := incorporation_json['filing']['incorporationApplication'].get('cooperative')):
        return [{
            'error': babel('cooperative data is missing in incorporationApplication.'),
            'path': '/filing/incorporationApplication/cooperative'
        }]

    msg = []

    rules_file_key = cooperative['rulesFileKey']
    rules_file_key_path = '/filing/incorporationApplication/cooperative/rulesFileKey'
    rules_err = validate_pdf(
        file_key=rules_file_key,
        file_key_path=rules_file_key_path,
        document_class=DocumentClasses.COOP.value
    )
    if rules_err:
        msg.extend(rules_err)

    memorandum_file_key = cooperative['memorandumFileKey']
    memorandum_file_key_path = '/filing/incorporationApplication/cooperative/memorandumFileKey'
    memorandum_err = validate_pdf(
        file_key=memorandum_file_key,
        file_key_path=memorandum_file_key_path,
        document_class=DocumentClasses.COOP.value
    )
    if memorandum_err:
        msg.extend(memorandum_err)

    return msg


def validate_ia_court_order(filing: dict) -> list:
    """Validate court order."""
    if court_order := filing.get('filing', {}).get('incorporationApplication', {}).get('courtOrder', None):
        court_order_path: Final = '/filing/incorporationApplication/courtOrder'
        err = validate_court_order(court_order_path, court_order)
        if err:
            return err
    return []
