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
import xml.etree.ElementTree as Et
from contextlib import suppress
from http import HTTPStatus
from pathlib import Path

import requests
from entity_queue_common.service_utils import QueueException
from flask import current_app
from jinja2 import Template
from legal_api.models import Business, PartyRole, RequestTracker
from legal_api.utils.datetime import datetime
from legal_api.utils.legislation_datetime import LegislationDatetime

from entity_bn.exceptions import BNException

from . import business_sub_type_code, business_type_code, program_type_code


def process(business: Business):  # pylint: disable=too-many-branches
    """Process the incoming registration request."""
    max_retry = current_app.config.get('MAX_RETRY')
    request_trackers = RequestTracker.find_by(business.id,
                                              RequestTracker.ServiceName.BN_HUB,
                                              RequestTracker.RequestType.INFORM_CRA)
    if not request_trackers:
        inform_cra_tracker = RequestTracker()
        inform_cra_tracker.business_id = business.id
        inform_cra_tracker.request_type = RequestTracker.RequestType.INFORM_CRA
        inform_cra_tracker.service_name = RequestTracker.ServiceName.BN_HUB
    else:
        inform_cra_tracker = request_trackers.pop()
        inform_cra_tracker.last_modified = datetime.utcnow()
        inform_cra_tracker.retry_number += 1

    _inform_cra(business, inform_cra_tracker)

    if not inform_cra_tracker.is_processed:
        if inform_cra_tracker.retry_number < max_retry:
            raise BNException(f'Retry number: {inform_cra_tracker.retry_number + 1}' +
                              f' for {business.identifier}, TrackerId: {inform_cra_tracker.id}.')

        raise QueueException(
            f'Retry exceeded the maximum count for {business.identifier}, TrackerId: {inform_cra_tracker.id}.')

    request_trackers = RequestTracker.find_by(business.id,
                                              RequestTracker.ServiceName.BN_HUB,
                                              RequestTracker.RequestType.GET_BN)

    if not request_trackers:
        get_bn_tracker = RequestTracker()
        get_bn_tracker.business_id = business.id
        get_bn_tracker.request_type = RequestTracker.RequestType.GET_BN
        get_bn_tracker.service_name = RequestTracker.ServiceName.BN_HUB
    else:
        get_bn_tracker = request_trackers.pop()
        get_bn_tracker.last_modified = datetime.utcnow()
        get_bn_tracker.retry_number += 1

    _get_bn(business, get_bn_tracker)

    if not get_bn_tracker.is_processed:
        if get_bn_tracker.retry_number < max_retry:
            raise BNException(f'Retry number: {get_bn_tracker.retry_number + 1}' +
                              f' for {business.identifier}, TrackerId: {get_bn_tracker.id}.')

        raise QueueException(
            f'Retry exceeded the maximum count for {business.identifier}, TrackerId: {get_bn_tracker.id}.')


def _inform_cra(business: Business, request_tracker: RequestTracker):
    """Inform CRA about new registration."""
    if request_tracker.is_processed:
        return

    founding_date = LegislationDatetime.as_legislation_timezone(business.founding_date).strftime('%Y-%m-%d')
    parties = [party_role.party for party_role in business.party_roles.all()
               if party_role.role.lower() in (PartyRole.RoleTypes.PARTNER.value, PartyRole.RoleTypes.PROPRIETOR.value)]

    input_xml = _build_input_xml('create_program_account_request', {
        'business': business.json(),
        'program_type_code': program_type_code[business.legal_type],
        'business_type_code': business_type_code[business.legal_type],
        'business_sub_type_code': business_sub_type_code[business.legal_type],
        'founding_date': founding_date,
        'legal_names': ','.join(party.name for party in parties),
        'parties': [party.json for party in parties],
        'delivery_address': business.delivery_address.one_or_none().json,
        'mailing_address': business.mailing_address.one_or_none().json
    })

    request_tracker.request_object = input_xml
    response = _request_bn(input_xml)
    if response.status_code == HTTPStatus.OK:
        with suppress(Et.ParseError):
            root = Et.fromstring(response.content)
            if root.tag == 'SBNAcknowledgement':
                request_tracker.is_processed = True
    request_tracker.response_object = response.text
    request_tracker.save()


def _get_bn(business: Business, request_tracker: RequestTracker):
    """Get business number from CRA."""
    if request_tracker.is_processed:
        return

    input_xml = _build_input_xml('basic_information_search_request', {
        'legal_name': business.legal_name,
        'business_type_code': business_type_code[business.legal_type],
    })

    request_tracker.request_object = input_xml
    response = _request_bn(input_xml)
    if response.status_code == HTTPStatus.OK:
        with suppress(Et.ParseError):
            root = Et.fromstring(response.content)
            if root.tag == 'SBNClientBasicInformationSearchResponse' and (
                    business_number := root.find('./body/clientBasicInformationSearchResult/businessRegistrationNumber')
            ) is not None:
                business.tax_id = business_number.text
                business.save()
                request_tracker.is_processed = True
    request_tracker.response_object = response.text
    request_tracker.save()


def _build_input_xml(template_name, data):
    """Build input XML."""
    template = Path(
        f'{current_app.config.get("TEMPLATE_PATH")}/{template_name}.xml'
    ).read_text()
    jnja_template = Template(template, autoescape=True)
    return jnja_template.render(data)


def _request_bn(input_xml):
    """Get request to BN Hub."""
    url = f'{current_app.config.get("BN_HUB_API_URL")}?inputXML={input_xml}'
    username = current_app.config.get('BN_HUB_CLIENT_ID')
    secret = current_app.config.get('BN_HUB_CLIENT_SECRET')
    return requests.get(url=url, auth=(username, secret))
