# Copyright © 2023 Province of British Columbia
#
# Licensed under the BSD 3 Clause License, (the 'License');
# you may not use this file except in compliance with the License.
# The template for the license can be found here
#    https://opensource.org/license/bsd-3-clause/
#
# Redistribution and use in source and binary forms,
# with or without modification, are permitted provided that the
# following conditions are met:
#
# 1. Redistributions of source code must retain the above copyright notice,
#    this list of conditions and the following disclaimer.
#
# 2. Redistributions in binary form must reproduce the above copyright notice,
#    this list of conditions and the following disclaimer in the documentation
#    and/or other materials provided with the distribution.
#
# 3. Neither the name of the copyright holder nor the names of its contributors
#    may be used to endorse or promote products derived from this software
#    without specific prior written permission.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS “AS IS”
# AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO,
# THE IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE
# ARE DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT HOLDER OR CONTRIBUTORS BE
# LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR
# CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF
# SUBSTITUTE GOODS OR SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS
# INTERRUPTION) HOWEVER CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN
# CONTRACT, STRICT LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE)
# ARISING IN ANY WAY OUT OF THE USE OF THIS SOFTWARE, EVEN IF ADVISED OF THE
# POSSIBILITY OF SUCH DAMAGE.
#
"""This Module processes simple cloud event messages for auth communication.
"""
from dataclasses import dataclass
from datetime import datetime, timezone
from http import HTTPStatus
from typing import Optional

from business_model import AlternateName, BusinessCommon, EntityRole, Filing, LegalEntity, RegistrationBootstrap
from flask import Blueprint, current_app, request
from simple_cloudevent import SimpleCloudEvent
from sqlalchemy.exc import OperationalError

from entity_auth.exceptions import AccountServiceException
from entity_auth.services import name_request, queue
from entity_auth.services.bootstrap import AccountService
from entity_auth.services.logging import structured_log


@dataclass
class Message:
    """Worker message class"""

    id: Optional[str] = None
    type: Optional[str] = None
    filing_id: Optional[str] = None
    identifier: Optional[str] = None


bp = Blueprint("worker", __name__)


@bp.route("/", methods=("POST",))
def worker():
    """Process the incoming cloud event.

    Flow
    --------
    1. Get cloud event
    2. Get filing and business information
    3. Update auth with business data

    Decisions on returning a 2xx or failing value to
    the Queue should be noted here:
    - Empty or garbaled messages are knocked off the Q
    - If there's no matching filing, put back on Q
    """
    structured_log(request, "INFO", f"Incoming raw msg: {request.data}")

    # 1. Get cloud event
    # ##
    if not (ce := queue.get_simple_cloud_event(request)):
        #
        # Decision here is to return a 200,
        # so the event is removed from the Queue
        return {}, HTTPStatus.OK

    structured_log(request, "INFO", f"received ce: {str(ce)}")

    # 2. Get information
    # ##
    if not (message := get_message(ce)):
        # no info, take off Q
        return {}, HTTPStatus.OK

    # 3. Process request
    # ##
    try:
        process_request(message)
        structured_log(request, "INFO", f"completed ce: {str(ce)}")
        return {}, HTTPStatus.OK

    except OperationalError:
        structured_log(request, "ERROR", f"Queue Blocked - Database Issue: {str(ce)}")
        return {}, HTTPStatus.BAD_REQUEST
        # We don't want to handle the error, as a DB down would drain the queue
    except AccountServiceException:
        structured_log(request, "ERROR", f"Account service issue: {str(ce)}")
        return {}, HTTPStatus.BAD_REQUEST
    except Exception as err:  # pylint: disable=broad-except
        # Catch Exception so that any error is still caught and the message is removed from the queue
        structured_log(request, "ERROR", f"Queue Error: {err}, {str(ce)}")
        return {}, HTTPStatus.OK  # Event is removed from the Queue


def get_message(ce: SimpleCloudEvent):
    """Return message in the cloud event."""
    if (data := ce.data) and isinstance(data, dict):
        msg = Message()
        msg.id = ce.id
        msg.type = ce.type
        msg.filing_id = ce.data.get("filingId")
        msg.identifier = ce.data.get("identifier")
        return msg
    return None


def process_request(
    msg: Message,
):  # pylint: disable=too-many-branches,too-many-statements
    """Process request."""

    filing: Filing = Filing.find_by_id(msg.filing_id)
    if not filing:
        raise Exception  # pylint: disable=broad-exception-raised

    business = fetch_business_by_filing(filing)
    if not business:
        raise Exception  # pylint: disable=broad-exception-raised

    name_request.consume_nr(business, filing)

    if filing.filing_type in [
        Filing.FilingTypes.AMALGAMATIONAPPLICATION.value,
        Filing.FilingTypes.INCORPORATIONAPPLICATION.value,
        Filing.FilingTypes.REGISTRATION.value,
    ]:
        create_affiliation(business, filing)
        return

    state = None
    if filing.filing_type in [Filing.FilingTypes.ALTERATION.value, Filing.FilingTypes.CHANGEOFREGISTRATION.value] or (
        filing.filing_type == Filing.FilingTypes.CORRECTION.value
        and business.entity_type
        in [
            BusinessCommon.EntityTypes.SOLE_PROP.value,
            BusinessCommon.EntityTypes.PARTNERSHIP.value,
            BusinessCommon.EntityTypes.COMP.value,
            BusinessCommon.EntityTypes.BCOMP.value,
            BusinessCommon.EntityTypes.BC_CCC.value,
            BusinessCommon.EntityTypes.BC_ULC_COMPANY.value,
            BusinessCommon.EntityTypes.COOP.value,
        ]
    ):
        state = None
    elif filing.filing_type == Filing.FilingTypes.DISSOLUTION.value:
        state = BusinessCommon.State.HISTORICAL.name
    elif filing.filing_type in [Filing.FilingTypes.PUTBACKON.value, Filing.FilingTypes.RESTORATION.value]:
        state = BusinessCommon.State.ACTIVE.name
    else:
        return

    status_code = AccountService.update_entity(
        business_registration=business.identifier,
        business_name=business.business_name,
        corp_type_code=business.entity_type,
        state=state,
    )
    if status_code != HTTPStatus.OK:
        raise AccountServiceException


def create_affiliation(business: AlternateName | LegalEntity, filing: Filing):
    """Create an affiliation for the business and remove the bootstrap."""

    try:
        bootstrap = RegistrationBootstrap.find_by_identifier(filing.temp_reg)
        corp_type_temp_code = "TMP"
        pass_code = ""
        details = None

        nr_number = filing.filing_json.get("filing").get(filing.filing_type, {}).get("nameRequest", {}).get("nrNumber")
        if filing.filing_type == Filing.FilingTypes.REGISTRATION.value:
            corp_type_temp_code = "RTMP"
            pass_code = get_firm_affiliation_passcode(business)

            details = {
                "bootstrapIdentifier": bootstrap.identifier,
                "identifier": business.identifier,
                "nrNumber": nr_number,
            }
        elif filing.filing_type == Filing.FilingTypes.AMALGAMATIONAPPLICATION.value:
            corp_type_temp_code = "ATMP"
            details = {
                "bootstrapIdentifier": bootstrap.identifier,
                "identifier": business.identifier,
                "nrNumber": nr_number,
            }

        rv = AccountService.create_affiliation(
            account=bootstrap.account,
            business_registration=business.identifier,
            business_name=business.business_name,
            corp_type_code=business.entity_type,
            pass_code=pass_code,
            details=details,
        )

        if rv not in (HTTPStatus.OK, HTTPStatus.CREATED):
            deaffiliation = AccountService.delete_affiliation(bootstrap.account, business.identifier)
            current_app.logger.error(
                f"Queue Error: Unable to affiliate business:{business.identifier} for filing:{filing.id}"
            )
        else:
            # update the bootstrap to use the new business identifier for the name
            bootstrap_update = AccountService.update_entity(
                business_registration=bootstrap.identifier,
                business_name=business.identifier,
                corp_type_code=corp_type_temp_code,
            )

        if (
            rv not in (HTTPStatus.OK, HTTPStatus.CREATED)
            or ("deaffiliation" in locals() and deaffiliation != HTTPStatus.OK)
            or ("bootstrap_update" in locals() and bootstrap_update != HTTPStatus.OK)
        ):
            raise Exception  # pylint: disable=broad-exception-raised
    except Exception as err:  # pylint: disable=broad-except; note out any exception, but don't fail the call
        current_app.logger.error(f"Queue Error: Affiliation error for filing:{filing.id}, with err:{err}")
        raise AccountServiceException from err


def get_firm_affiliation_passcode(business: AlternateName | LegalEntity):
    """Return a firm passcode for a given business identifier."""
    pass_code = None
    end_date = datetime.now(timezone.utc).date()

    if business.is_alternate_name_entity and business.entity_type == BusinessCommon.EntityTypes.SOLE_PROP.value:
        if business.is_owned_by_legal_entity_person:
            pass_code = business.legal_entity.last_name + ", " + business.legal_entity.first_name
            if business.legal_entity.middle_initial:
                pass_code = pass_code + " " + business.legal_entity.middle_initial
        elif business.is_owned_by_legal_entity_org:
            pass_code = business.legal_name
        elif business.is_owned_by_colin_entity:
            pass_code = business.colin_entity.organization_name

    elif entity_roles := EntityRole.get_entity_roles(business.id, end_date):
        entity_role = entity_roles[0]
        if entity_role.is_related_colin_entity:
            pass_code = entity_role.related_colin_entity.name
        else:
            party = entity_role.related_entity
            if party.entity_type == "organization":
                pass_code = party.legal_name
            else:
                pass_code = party.last_name + ", " + party.first_name
                if hasattr(party, "middle_initial") and party.middle_initial:
                    pass_code = pass_code + " " + party.middle_initial

    return pass_code


def fetch_business_by_filing(filing):  # pylint: disable=redefined-builtin
    """Fetches appropriate business from a filing.

    This can be an instance of legal entity or alternate name.
    """
    if (legal_entity_id := filing.legal_entity_id) and (
        legal_entity := LegalEntity.find_by_internal_id(legal_entity_id)
    ):
        return legal_entity

    if (alternate_name_id := filing.alternate_name_id) and (
        alternate_name := AlternateName.find_by_internal_id(alternate_name_id)
    ):
        return alternate_name

    return None
