# Copyright © 2025 Province of British Columbia
#
# Licensed under the BSD 3 Clause License, (the "License");
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
"""Manages the type of Business."""
import json
import traceback
from http import HTTPStatus

import requests
from business_model.models import Business, Filing, RegistrationBootstrap
from flask import current_app
from flask_babel import _ as babel

from business_filer.exceptions import QueueException
from business_filer.filing_processors.filing_components import business_info
from business_filer.services import AccountService, Flags


def update_business_profile(business: Business,
                            filing: Filing,
                            filing_type: str | None = None):
    """Update business profile."""
    if Flags.is_on("enable-sandbox"):
        current_app.logger.info("Skip updating business profile")
        return

    filing_type = filing_type if filing_type else filing.filing_type
    if ((contact_point := filing.filing_json["filing"][filing_type].get("contactPoint"))
        and
        (err := _update_business_profile(business, contact_point))):
            current_app.logger.info(
                f"Queue Error: Update Business for filing:{filing.id}, error:{err}",
                level="error")


def _update_business_profile(business: Business, profile_info: dict) -> dict:
    """Update business profile with email and phone no."""
    if not business or not profile_info:
        return {"error": babel("Business and profile_info required.")}

    # contact phone is optional
    phone = profile_info.get("phone", "")

    error = {"error": "Unknown handling"}
    if email := profile_info.get("email"):
        # assume the JSONSchema ensures it is a valid email format
        token = AccountService.get_bearer_token()
        account_svc_entity_url = current_app.config["ACCOUNT_SVC_ENTITY_URL"]

        # Create an entity record
        data = json.dumps(
            {"email": email,
             "phone": phone,
             "phoneExtension": ""
             }
        )
        url = "".join([account_svc_entity_url, "/", business.identifier, "/contacts"])
        rv = requests.post(
            url=url,
            headers={**AccountService.CONTENT_TYPE_JSON,
                     "Authorization": AccountService.BEARER + token},
            data=data,
            timeout=AccountService.timeout
        )
        if rv.status_code in (HTTPStatus.OK, HTTPStatus.CREATED):
            error = None

        if rv.status_code == HTTPStatus.NOT_FOUND:
            error = {"error": "No business profile found."}

        if rv.status_code == HTTPStatus.METHOD_NOT_ALLOWED:
            error = {"error": "Service account missing privileges to update business profiles"}

        if rv.status_code == HTTPStatus.BAD_REQUEST and \
                "DATA_ALREADY_EXISTS" in rv.text:
            put = requests.put(
                url="".join([account_svc_entity_url, "/", business.identifier, "/contacts"]),
                headers={**AccountService.CONTENT_TYPE_JSON,
                         "Authorization": AccountService.BEARER + token},
                data=data,
                timeout=AccountService.timeout
            )
            if put.status_code in (HTTPStatus.OK, HTTPStatus.CREATED):
                error = None
            else:
                error = {"error": "Unable to update existing business profile."}

    return error


def update_affiliation(business: Business, filing: Filing):
    """Create an affiliation for the business and remove the bootstrap."""
    try:
        current_app.logger.info("Updating affiliation for business")
        bootstrap = RegistrationBootstrap.find_by_identifier(filing.temp_reg)

        pass_code = ""
        if filing.filing_type == "registration":
            pass_code = business_info.get_firm_affiliation_passcode(business.id)

        nr_number = (filing.filing_json
                     .get("filing")
                     .get(filing.filing_type, {})
                     .get("nameRequest", {})
                     .get("nrNumber"))
        details = {
            "bootstrapIdentifier": bootstrap.identifier,
            "identifier": business.identifier,
            "nrNumber": nr_number
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
            current_app.logger.error(f"Unable to affiliate business:{business.identifier} for filing:{filing.id}")
            current_app.logger.info(
                f"Queue Error: Unable to affiliate business:{business.identifier} for filing:{filing.id}",
                level="error"
            )
        else:
            # update the bootstrap to use the new business identifier for the name
            bootstrap_update = AccountService.update_entity(
                business_registration=bootstrap.identifier,
                business_name=business.identifier,
                corp_type_code=Filing.FILINGS[filing.filing_type]["temporaryCorpTypeCode"]
            )

        # pylint: disable=possibly-used-before-assignment;
        if (rv not in (HTTPStatus.OK, HTTPStatus.CREATED)
            or ("deaffiliation" in locals() and deaffiliation != HTTPStatus.OK)
                or ("bootstrap_update" in locals() and bootstrap_update != HTTPStatus.OK)):
            raise QueueException
    except Exception as err:  # pylint: disable=broad-except; note out any exception, but don't fail the call
        current_app.logger.error(f"Affiliation error for filing:{filing.id}, with err:{err}")
        current_app.logger.debug(traceback.format_exc())
        current_app.logger.info(
            f"Queue Error: Affiliation error for filing:{filing.id}, with err:{err}",
            level="error"
        )


def update_entity(business: Business, filing_type: str):
    """Update an entity in auth with the latest change."""
    state = None
    if filing_type in ["amalgamationOut", "continuationOut", "dissolution", "putBackOn", "putBackOff", "restoration"]:
        state = business.state.name  # state changed to HISTORICAL/ACTIVE

    AccountService.update_entity(
        business_registration=business.identifier,
        business_name=business.legal_name,
        corp_type_code=business.legal_type,
        state=state
    )
