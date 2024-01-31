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
from flask import current_app
from legal_api.models import (
    Address,
    EntityRole,
    Filing,
    LegalEntity,
    RequestTracker,
    db,
)
from legal_api.utils.datetime import datetime
from legal_api.utils.legislation_datetime import LegislationDatetime
from sqlalchemy import and_

from entity_bn.bn_processors import (
    bn_note,
    build_input_xml,
    document_sub_type,
    get_splitted_business_number,
    request_bn_hub,
)
from entity_bn.exceptions import BNException, BNRetryExceededException


def process(legal_entity: LegalEntity, filing: Filing):  # pylint: disable=too-many-branches
    """Process the incoming change of registration request."""
    if filing.meta_data and filing.meta_data.get("changeOfRegistration", {}).get("toBusinessName"):
        change_name(legal_entity, filing, RequestTracker.RequestType.CHANGE_NAME)

    with suppress(KeyError, ValueError):
        if dpath.util.get(filing.filing_json, "filing/changeOfRegistration/parties") and has_party_name_changed(
            legal_entity, filing
        ):
            change_name(legal_entity, filing, RequestTracker.RequestType.CHANGE_PARTY)

    with suppress(KeyError, ValueError):
        if dpath.util.get(filing.filing_json, "filing/changeOfRegistration/offices/businessOffice"):
            if has_previous_address(
                filing.id,
                legal_entity.office_delivery_address.one_or_none().office_id,
                "delivery",
            ):
                change_address(
                    legal_entity,
                    filing,
                    RequestTracker.RequestType.CHANGE_DELIVERY_ADDRESS,
                )

            if has_previous_address(
                filing.id,
                legal_entity.office_mailing_address.one_or_none().office_id,
                "mailing",
            ):
                change_address(
                    legal_entity,
                    filing,
                    RequestTracker.RequestType.CHANGE_MAILING_ADDRESS,
                )


def change_name(
    legal_entity: LegalEntity,
    filing: Filing,  # pylint: disable=too-many-locals
    name_type: RequestTracker.RequestType,
):
    """Inform CRA about change of name."""
    max_retry = current_app.config.get("BN_HUB_MAX_RETRY")
    request_trackers = RequestTracker.find_by(legal_entity.id, RequestTracker.ServiceName.BN_HUB, name_type, filing.id)
    if not request_trackers:
        request_tracker = RequestTracker()
        request_tracker.legal_entity_id = legal_entity.id
        request_tracker.filing_id = filing.id
        request_tracker.request_type = name_type
        request_tracker.service_name = RequestTracker.ServiceName.BN_HUB
        request_tracker.retry_number = 0
        request_tracker.is_processed = False
    elif (request_tracker := request_trackers.pop()) and not request_tracker.is_processed:
        request_tracker.last_modified = datetime.utcnow()
        request_tracker.retry_number += 1

    if request_tracker.is_processed:
        return

    client_name_type_code = {
        RequestTracker.RequestType.CHANGE_PARTY: "01",
        RequestTracker.RequestType.CHANGE_NAME: "02",
    }
    update_reason_code = {
        RequestTracker.RequestType.CHANGE_PARTY: "03",
        RequestTracker.RequestType.CHANGE_NAME: "01",
    }

    if name_type == RequestTracker.RequestType.CHANGE_NAME:
        new_name = legal_entity.business_name
    elif name_type == RequestTracker.RequestType.CHANGE_PARTY:
        new_name = legal_entity.legal_name

    alternate_name = legal_entity._alternate_names.first() # pylint: disable=protected-access
    bn15 = alternate_name.bn15

    input_xml = build_input_xml(
        "change_name",
        {
            "retryNumber": str(request_tracker.retry_number),
            "filingId": str(filing.id),
            "documentSubType": document_sub_type[name_type],
            "clientNameTypeCode": client_name_type_code[name_type],
            "updateReasonCode": update_reason_code[name_type],
            "newName": new_name,
            "business": legal_entity.json(),
            **get_splitted_business_number(bn15),
        },
    )

    request_tracker.request_object = input_xml
    if not bn15:
        request_tracker.response_object = bn_note
        request_tracker.save()
        return

    status_code, response = request_bn_hub(input_xml)
    if status_code == HTTPStatus.OK:
        with suppress(Et.ParseError):
            root = Et.fromstring(response)
            if root.tag == "SBNAcknowledgement":
                request_tracker.is_processed = True
    request_tracker.response_object = response
    request_tracker.save()

    if not request_tracker.is_processed:
        if request_tracker.retry_number < max_retry:
            raise BNException(
                f"Retry number: {request_tracker.retry_number + 1}"
                + f" for {legal_entity.identifier}, TrackerId: {request_tracker.id}."
            )

        raise BNRetryExceededException(
            f"Retry exceeded the maximum count for {legal_entity.identifier}, TrackerId: {request_tracker.id}."
        )


def change_address(
    legal_entity: LegalEntity,
    filing: Filing,  # pylint: disable=too-many-locals
    address_type: RequestTracker.RequestType,
):
    """Inform CRA about change of address."""
    max_retry = current_app.config.get("BN_HUB_MAX_RETRY")

    address_type_code = {
        RequestTracker.RequestType.CHANGE_DELIVERY_ADDRESS: "01",
        RequestTracker.RequestType.CHANGE_MAILING_ADDRESS: "02",
    }

    request_trackers = RequestTracker.find_by(
        legal_entity.id, RequestTracker.ServiceName.BN_HUB, address_type, filing.id
    )
    if not request_trackers:
        request_tracker = RequestTracker()
        request_tracker.legal_entity_id = legal_entity.id
        request_tracker.filing_id = filing.id
        request_tracker.request_type = address_type
        request_tracker.service_name = RequestTracker.ServiceName.BN_HUB
        request_tracker.retry_number = 0
        request_tracker.is_processed = False
    elif (request_tracker := request_trackers.pop()) and not request_tracker.is_processed:
        request_tracker.last_modified = datetime.utcnow()
        request_tracker.retry_number += 1

    if request_tracker.is_processed:
        return

    effective_date = LegislationDatetime.as_legislation_timezone(filing.effective_date).strftime("%Y-%m-%d")
    address = (
        legal_entity.office_delivery_address
        if address_type == RequestTracker.RequestType.CHANGE_DELIVERY_ADDRESS
        else legal_entity.office_mailing_address
    )

    alternate_name = legal_entity._alternate_names.first() # pylint: disable=protected-access
    bn15 = alternate_name.bn15

    input_xml = build_input_xml(
        "change_address",
        {
            "retryNumber": str(request_tracker.retry_number),
            "filingId": str(filing.id),
            "business": legal_entity.json(),
            "documentSubType": document_sub_type[address_type],
            "addressTypeCode": address_type_code[address_type],
            "effectiveDate": effective_date,
            "address": address.one_or_none().json,
            **get_splitted_business_number(bn15),
        },
    )

    request_tracker.request_object = input_xml
    if not bn15:
        request_tracker.response_object = bn_note
        request_tracker.save()
        return

    status_code, response = request_bn_hub(input_xml)
    if status_code == HTTPStatus.OK:
        with suppress(Et.ParseError):
            root = Et.fromstring(response)
            if root.tag == "SBNAcknowledgement":
                request_tracker.is_processed = True
    request_tracker.response_object = response
    request_tracker.save()

    if not request_tracker.is_processed:
        if request_tracker.retry_number < max_retry:
            raise BNException(
                f"Retry number: {request_tracker.retry_number + 1}"
                + f" for {legal_entity.identifier}, TrackerId: {request_tracker.id}."
            )

        raise BNRetryExceededException(
            f"Retry exceeded the maximum count for {legal_entity.identifier}, TrackerId: {request_tracker.id}."
        )


# TODO: Fix below functions (and add unit test) to check history data once we have clarity on the versioning changes
def has_previous_address(transaction_id: int, office_id: int, address_type: str) -> bool:
    """Has previous address for the given transaction and office id."""
    address_version = version_class(Address)
    address = (
        db.session.query(address_version)
        .filter(address_version.operation_type != 2)
        .filter(address_version.office_id == office_id)
        .filter(address_version.address_type == address_type)
        .filter(address_version.end_transaction_id == transaction_id)
        .one_or_none()
    )

    return bool(address)


def has_party_name_changed(legal_entity: LegalEntity, filing: Filing) -> bool:
    """Has party name changed in the given filing."""
    party_role_version = version_class(EntityRole)
    party_roles = (
        db.session.query(party_role_version)
        .filter(party_role_version.transaction_id == filing.transaction_id)
        .filter(party_role_version.operation_type != 2)
        .filter(party_role_version.business_id == business.id)
        .filter(party_role_version.role in (PartyRole.RoleTypes.PARTNER.value, PartyRole.RoleTypes.PROPRIETOR.value))
        .all()
    )

    if len(party_roles) > 0:  # New party added or party deleted by setting cessation_date
        return True

    party_names = {}
    for party_role in business.party_roles.all():
        if (
            party_role.role.lower() in (PartyRole.RoleTypes.PARTNER.value, PartyRole.RoleTypes.PROPRIETOR.value)
            and party_role.cessation_date is None
        ):
            party_names[party_role.party.id] = party_role.party.name

    parties = _get_modified_parties(filing.transaction_id, business.id)
    for party in parties:
        if party_names[party.id] != _get_name(party):
            return True

    return False


def _get_name(party) -> str:
    """Return the full name of the party for comparison."""
    if party.party_type == Party.PartyTypes.PERSON.value:
        if party.middle_initial:
            return " ".join((party.first_name, party.middle_initial, party.last_name)).strip().upper()
        return " ".join((party.first_name, party.last_name)).strip().upper()
    return party.organization_name.strip().upper()


def _get_modified_parties(transaction_id, business_id):
    """Get all party values before the given transaction id."""
    party_version = version_class(Party)
    parties = (
        db.session.query(party_version)
        .join(
            PartyRole,
            and_(
                PartyRole.party_id == party_version.id,
                PartyRole.business_id == business_id,
            ),
        )
        .filter(
            PartyRole.role.in_(
                [
                    PartyRole.RoleTypes.PARTNER.value,
                    PartyRole.RoleTypes.PROPRIETOR.value,
                ]
            )
        )
        .filter(party_version.operation_type != 2)
        .filter(party_version.end_transaction_id == transaction_id)
        .all()
    )
    return parties
