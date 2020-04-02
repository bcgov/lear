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
from http import HTTPStatus  # pylint: disable=wrong-import-order
from typing import Dict

import pycountry

from flask_babel import _ as babel  # noqa: N813, I004, I001, I003
from legal_api.errors import Error


def validate(incorporation_json: Dict):
    """Validate the Incorporation filing."""
    if not incorporation_json:
        return Error(HTTPStatus.BAD_REQUEST, [{'error': babel('A valid filing is required.')}])
    msg = []

    err = validate_offices(incorporation_json)
    if err:
        msg.append(err)

    err = validate_roles(incorporation_json)
    if err:
        msg.append(err)

    err = validate_parties_mailing_address(incorporation_json)
    if err:
        msg.append(err)

    err = validate_share_structure(incorporation_json)
    if err:
        msg.append(err)

    if msg:
        return Error(HTTPStatus.BAD_REQUEST, msg)
    return None


def validate_offices(incorporation_json) -> Error:
    """Validate the office addresses of the incorporation filing."""
    offices_array = incorporation_json['filing']['incorporationApplication']['offices']
    addresses = offices_array
    msg = []

    for item in addresses.keys():
        for k, v in addresses[item].items():
            region = v['addressRegion']
            country = v['addressCountry']

            if region != 'BC':
                path = '/filing/incorporationApplication/offices/%s/%s/addressRegion' % (
                    item, k
                )
                msg.append({'error': "Address Region must be 'BC'.",
                            'path': path})

            try:
                country = pycountry.countries.search_fuzzy(country)[0].alpha_2
                if country != 'CA':
                    raise LookupError
            except LookupError:
                err_path = '/filing/incorporationApplication/offices/%s/%s/addressCountry' % (
                    item, k
                )
                msg.append({'error': "Address Country must be 'CA'.",
                            'path': err_path})
    if msg:
        return msg

    return None


def validate_roles(incorporation_json) -> Error:
    """Validate the required completing party of the incorporation filing."""
    parties_array = incorporation_json['filing']['incorporationApplication']['parties']
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

    if completing_party_count == 0:
        err_path = '/filing/incorporationApplication/parties/roles'
        msg.append({'error': 'Must have a minimum of one completing party', 'path': err_path})

    if completing_party_count > 1:
        err_path = '/filing/incorporationApplication/parties/roles'
        msg.append({'error': 'Must have a maximum of one completing party', 'path': err_path})

    if incorporation_json['filing']['incorporationApplication']['nameRequest']['legalType'] == 'BC':
        if incorporator_count < 1:
            err_path = '/filing/incorporationApplication/parties/roles'
            msg.append({'error': 'Must have a minimum of one Incorporator', 'path': err_path})

        if director_count < 1:
            err_path = '/filing/incorporationApplication/parties/roles'
            msg.append({'error': 'Must have a minimum of one Director', 'path': err_path})

    if msg:
        return msg

    return None


def validate_parties_mailing_address(incorporation_json) -> Error:
    """Validate the person data of the incorporation filing."""
    parties_array = incorporation_json['filing']['incorporationApplication']['parties']
    msg = []

    for item in parties_array:
        for k, v in item['mailingAddress'].items():
            if v is None:
                err_path = '/filing/incorporationApplication/parties/%s/mailingAddress/%s/%s/' % (
                    item['officer']['id'], k, v
                )
                msg.append({'error': 'Person %s: Mailing address %s %s is invalid' % (
                    item['officer']['id'], k, v
                ),
                            'path': err_path})

    if msg:
        return msg

    return None


def validate_share_structure(incorporation_json) -> Error:
    """Validate the share structure data of the incorporation filing."""
    share_classes = incorporation_json['filing']['incorporationApplication']['shareClasses']
    msg = []

    for index, item in enumerate(share_classes):
        if item['hasMaximumShares']:
            if not item.get('maxNumberOfShares', None):
                err_path = '/filing/incorporationApplication/shareClasses/%s/maxNumberOfShares/' % index
                msg.append({'error': 'Share class %s must provide value for maximum number of shares' % item['name'],
                            'path': err_path})
        if item['hasParValue']:
            if not item.get('parValue', None):
                err_path = '/filing/incorporationApplication/shareClasses/%s/parValue/' % index
                msg.append({'error': 'Share class %s must specify par value' % item['name'], 'path': err_path})
            if not item.get('currency', None):
                err_path = '/filing/incorporationApplication/shareClasses/%s/currency/' % index
                msg.append({'error': 'Share class %s must specify currency' % item['name'], 'path': err_path})
        for series_index, series in enumerate(item.get('series', [])):
            err_path = '/filing/incorporationApplication/shareClasses/%s/series/%s' % (index, series_index)
            if series['hasMaximumShares']:
                if not series.get('maxNumberOfShares', None):
                    msg.append({
                        'error': 'Share series %s must provide value for maximum number of shares' % series['name'],
                        'path': '%s/maxNumberOfShares' % err_path
                    })
                else:
                    if item['hasMaximumShares'] and item.get('maxNumberOfShares', None) and \
                            series['maxNumberOfShares'] > item['maxNumberOfShares']:
                        msg.append({
                            'error': 'Series %s share quantity must be less than or equal to that of its class %s'
                                     % (series['name'], item['name']),
                            'path': '%s/maxNumberOfShares' % err_path
                        })

    if msg:
        return msg

    return None
