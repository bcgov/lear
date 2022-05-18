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
"""File processing rules and actions for the change of registration of a business."""
import xml.etree.ElementTree as Et
from contextlib import suppress
from http import HTTPStatus

import dpath
from entity_queue_common.service_utils import QueueException
from flask import current_app
from legal_api.models import Address, Business, Filing, RequestTracker, db
from legal_api.utils.datetime import datetime
from legal_api.utils.legislation_datetime import LegislationDatetime
from sqlalchemy_continuum import version_class

from entity_bn.bn_processors import build_input_xml, document_sub_type, request_bn_hub
from entity_bn.exceptions import BNException


def process(business: Business, filing: Filing):  # pylint: disable=too-many-branches
    """Process the incoming change of registration request."""
    if not business.tax_id or len(business.tax_id) != 15:
        raise BNException(f'Business {business.identifier}, ' +
                          'Cannot inform CRA about change of registration before receiving Business Number (BN15).')

    if filing.meta_data and filing.meta_data.get('changeOfRegistration', {}).get('toLegalName'):
        _change_name(business, filing, RequestTracker.RequestType.CHANGE_NAME)

    with suppress(KeyError, ValueError):
        if dpath.util.get(filing.filing_json, 'filing/changeOfRegistration/offices/businessOffice'):
            if has_previous_address(filing.transaction_id,
                                    business.delivery_address.one_or_none().office_id, 'delivery'):
                _change_address(business, filing, RequestTracker.RequestType.CHANGE_DELIVERY_ADDRESS)

            if has_previous_address(filing.transaction_id,
                                    business.mailing_address.one_or_none().office_id, 'mailing'):
                _change_address(business, filing, RequestTracker.RequestType.CHANGE_MAILING_ADDRESS)


def _change_name(business: Business, filing: Filing, name_type: RequestTracker.RequestType):
    """Inform CRA about change of name."""
    max_retry = current_app.config.get('BN_HUB_MAX_RETRY')
    request_trackers = RequestTracker.find_by(business.id,
                                              RequestTracker.ServiceName.BN_HUB,
                                              RequestTracker.RequestType.CHANGE_NAME,
                                              filing.id)
    if not request_trackers:
        request_tracker = RequestTracker()
        request_tracker.business_id = business.id
        request_tracker.filing_id = filing.id
        request_tracker.request_type = RequestTracker.RequestType.CHANGE_NAME
        request_tracker.service_name = RequestTracker.ServiceName.BN_HUB
    elif (request_tracker := request_trackers.pop()) and not request_tracker.is_processed:
        request_tracker.last_modified = datetime.utcnow()
        request_tracker.retry_number += 1

    if request_tracker.is_processed:
        return

    business_registration_number = business.tax_id[0:9]
    business_program_identifier = business.tax_id[9:11]
    business_program_account_reference_number = business.tax_id[11:15]

    client_name_type_code = {
        # RequestTracker.RequestType.CHANGE_PARTY: '01',
        RequestTracker.RequestType.CHANGE_NAME: '02'
    }
    update_reason_code = {
        # RequestTracker.RequestType.CHANGE_PARTY: '03',
        RequestTracker.RequestType.CHANGE_NAME: '01'
    }

    new_name = business.legal_name if name_type == RequestTracker.RequestType.CHANGE_NAME else ''

    input_xml = build_input_xml('change_name', {
        'documentSubType': document_sub_type[name_type],
        'clientNameTypeCode': client_name_type_code[name_type],
        'updateReasonCode': update_reason_code[name_type],
        'newName': new_name,
        'business': business.json(),
        'businessRegistrationNumber': business_registration_number,
        'businessProgramIdentifier': business_program_identifier,
        'businessProgramAccountReferenceNumber': business_program_account_reference_number
    })

    request_tracker.request_object = input_xml
    status_code, response = request_bn_hub(input_xml)
    if status_code == HTTPStatus.OK:
        with suppress(Et.ParseError):
            root = Et.fromstring(response)
            if root.tag == 'SBNAcknowledgement':
                request_tracker.is_processed = True
    request_tracker.response_object = response
    request_tracker.save()

    if not request_tracker.is_processed:
        if request_tracker.retry_number < max_retry:
            raise BNException(f'Retry number: {request_tracker.retry_number + 1}' +
                              f' for {business.identifier}, TrackerId: {request_tracker.id}.')

        raise QueueException(
            f'Retry exceeded the maximum count for {business.identifier}, TrackerId: {request_tracker.id}.')


def _change_address(business: Business, filing: Filing, address_type: RequestTracker.RequestType):
    """Inform CRA about change of address."""
    max_retry = current_app.config.get('BN_HUB_MAX_RETRY')

    address_type_code = {
        RequestTracker.RequestType.CHANGE_DELIVERY_ADDRESS: '01',
        RequestTracker.RequestType.CHANGE_MAILING_ADDRESS: '02'
    }

    request_trackers = RequestTracker.find_by(business.id,
                                              RequestTracker.ServiceName.BN_HUB,
                                              address_type,
                                              filing.id)
    if not request_trackers:
        request_tracker = RequestTracker()
        request_tracker.business_id = business.id
        request_tracker.filing_id = filing.id
        request_tracker.request_type = address_type
        request_tracker.service_name = RequestTracker.ServiceName.BN_HUB
    elif (request_tracker := request_trackers.pop()) and not request_tracker.is_processed:
        request_tracker.last_modified = datetime.utcnow()
        request_tracker.retry_number += 1

    if request_tracker.is_processed:
        return

    business_registration_number = business.tax_id[0:9]
    business_program_identifier = business.tax_id[9:11]
    business_program_account_reference_number = business.tax_id[11:15]

    effective_date = LegislationDatetime.as_legislation_timezone(filing.effective_date).strftime('%Y-%m-%d')
    address = (business.delivery_address
               if address_type == RequestTracker.RequestType.CHANGE_DELIVERY_ADDRESS
               else business.mailing_address)
    input_xml = build_input_xml('change_address', {
        'business': business.json(),
        'documentSubType': document_sub_type[address_type],
        'addressTypeCode': address_type_code[address_type],
        'effectiveDate': effective_date,
        'address': address.one_or_none().json,
        'businessRegistrationNumber': business_registration_number,
        'businessProgramIdentifier': business_program_identifier,
        'businessProgramAccountReferenceNumber': business_program_account_reference_number
    })

    request_tracker.request_object = input_xml
    status_code, response = request_bn_hub(input_xml)
    if status_code == HTTPStatus.OK:
        with suppress(Et.ParseError):
            root = Et.fromstring(response)
            if root.tag == 'SBNAcknowledgement':
                request_tracker.is_processed = True
    request_tracker.response_object = response
    request_tracker.save()

    if not request_tracker.is_processed:
        if request_tracker.retry_number < max_retry:
            raise BNException(f'Retry number: {request_tracker.retry_number + 1}' +
                              f' for {business.identifier}, TrackerId: {request_tracker.id}.')

        raise QueueException(
            f'Retry exceeded the maximum count for {business.identifier}, TrackerId: {request_tracker.id}.')


def has_previous_address(transaction_id, office_id, address_type) -> dict:
    """Has previous address for the given transaction and office id."""
    address_version = version_class(Address)
    address = db.session.query(address_version) \
        .filter(address_version.operation_type != 2) \
        .filter(address_version.office_id == office_id) \
        .filter(address_version.address_type == address_type) \
        .filter(address_version.end_transaction_id == transaction_id).one_or_none()

    return True if address else False
