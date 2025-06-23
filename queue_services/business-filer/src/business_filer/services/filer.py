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
"""The unique worker functionality for this service is contained here.
"""
import json

from business_model.models import Business, Filing, db
from business_model.models.db import VersioningProxy
from flask import current_app

from business_filer.common.filing import FilingTypes
from business_filer.common.filing_message import FilingMessage
from business_filer.exceptions import DefaultError, QueueException
from business_filer.filing_meta import FilingMeta, json_serial
from business_filer.filing_processors import (
    admin_freeze,
    agm_extension,
    agm_location_change,
    alteration,
    amalgamation_application,
    amalgamation_out,
    annual_report,
    appoint_receiver,
    cease_receiver,
    change_of_address,
    change_of_directors,
    change_of_name,
    change_of_officers,
    change_of_registration,
    consent_amalgamation_out,
    consent_continuation_out,
    continuation_in,
    continuation_out,
    conversion,
    correction,
    court_order,
    dissolution,
    incorporation_filing,
    intent_to_liquidate,
    notice_of_withdrawal,
    put_back_off,
    put_back_on,
    registrars_notation,
    registrars_order,
    registration,
    restoration,
    special_resolution,
    transition,
    transparency_register,
)
from business_filer.filing_processors.filing_components import business_profile, name_request
from business_filer.services import flags
from business_filer.services.publish_event import PublishEvent


def get_filing_types(legal_filings: dict):
    """Get the filing type fee codes for the filing.

    Returns: {
        list: a list of filing types.
    }
    """
    filing_types = []
    for k in legal_filings["filing"]:
        if Filing.FILINGS.get(k, None):
            filing_types.append(k)
    return filing_types


def process_filing(filing_message: FilingMessage): # noqa: PLR0915, PLR0912
    """Render the filings contained in the submission."""
    if not (filing_submission := Filing.find_by_id(filing_message.filing_identifier)):
        current_app.logger.error(f"No filing found for: {filing_message}")
        raise DefaultError(error_text=f"filing not found for {filing_message.filing_identifier}")


    if filing_submission.status in [Filing.Status.COMPLETED, Filing.Status.WITHDRAWN]:
        current_app.logger.warning("QueueFiler: Attempting to reprocess business.id=%s, filing.id=%s filing=%s",
                                    filing_submission.business_id, filing_submission.id, filing_message)
        return None, None

    if filing_submission.withdrawal_pending:
        # TODO: set this better
        current_app.logger.warning("QueueFiler: NoW pending for this filing business.id=%s, filing.id=%s filing=%s",
                                    filing_submission.business_id, filing_submission.id, filing_message)
        raise QueueException("withdrawal_pending", 1 )

    # convenience flag to set that the envelope is a correction
    is_correction = filing_submission.filing_type == FilingTypes.CORRECTION

    if legal_filings := filing_submission.legal_filings():
        transaction_id = VersioningProxy.get_transaction_id(db.session())

        business = Business.find_by_internal_id(filing_submission.business_id)

        # Updating effective_date before processing the filing
        filing_submission.set_processed()

        filing_meta = FilingMeta(application_date=filing_submission.effective_date,
                                    legal_filings=[item for sublist in
                                                [list(x.keys()) for x in legal_filings]
                                                for item in sublist])
        if is_correction:
            filing_meta.correction = {}

        for filing in legal_filings:
            filing_type = next(iter(filing))

            match filing_type:
                case "adminFreeze":
                    admin_freeze.process(business, filing, filing_submission, filing_meta)

                case "agmExtension":
                    agm_extension.process(filing, filing_meta)

                case "agmLocationChange":
                    agm_location_change.process(filing, filing_meta)

                case "alteration":
                    alteration.process(business, filing_submission, filing, filing_meta, is_correction)

                case "amalgamationApplication":
                    business, filing_submission, filing_meta = amalgamation_application.process(
                        business,
                        filing_submission.json,
                        filing_submission,
                        filing_meta,
                        flags)

                case "amalgamationOut":
                    amalgamation_out.process(business, filing_submission, filing, filing_meta)

                case "annualReport":
                    flag_on = flags.is_on("enable-involuntary-dissolution")
                    current_app.logger.debug("enable-involuntary-dissolution flag on: %s", flag_on)
                    annual_report.process(business, filing, filing_meta, flag_on)

                case "appointReceiver":
                    appoint_receiver.process(business, filing, filing_submission, filing_meta)
 
                case "ceaseReceiver":
                    cease_receiver.process(business, filing, filing_submission, filing_meta)

                case "changeOfAddress":
                    flag_on = flags.is_on("enable-involuntary-dissolution")
                    change_of_address.process(business, filing, filing_meta, flag_on)

                case "changeOfDirectors":
                    change_of_directors.process(business, filing_submission, filing_meta)

                case "changeOfName":
                    change_of_name.process(business, filing, filing_meta)

                case "changeOfOfficers":
                    change_of_officers.process(business, filing_submission, filing_meta)

                case "changeOfRegistration":
                    change_of_registration.process(business, filing_submission, filing, filing_meta)

                case "consentAmalgamationOut":
                    consent_amalgamation_out.process(business, filing_submission, filing, filing_meta)

                case "consentContinuationOut":
                    consent_continuation_out.process(business, filing_submission, filing, filing_meta)

                case "continuationIn":
                    business, filing_submission, filing_meta = continuation_in.process(
                        business,
                        filing_submission.json,
                        filing_submission,
                        filing_meta,
                        flags)

                case "continuationOut":
                    continuation_out.process(business, filing_submission, filing, filing_meta)

                case "conversion":
                    business, filing_submission = conversion.process(business,
                                                                    filing_submission.json,
                                                                    filing_submission,
                                                                    filing_meta)

                case "correction":
                    filing_submission = correction.process(filing_submission, filing, filing_meta, business)

                case "courtOrder":
                    court_order.process(business, filing_submission, filing, filing_meta)

                case "dissolution":
                    flag_on = flags.is_on("enable-involuntary-dissolution")
                    dissolution.process(business, filing, filing_submission, filing_meta, flag_on)

                case "incorporationApplication":
                    business, filing_submission, filing_meta = \
                        incorporation_filing.process(business,
                                                    filing_submission.json,
                                                    filing_submission,
                                                    filing_meta,
                                                    flags)
                
                case "intentToLiquidate":
                    intent_to_liquidate.process(business, filing, filing_submission, filing_meta)

                case "noticeOfWithdrawal":
                    notice_of_withdrawal.process(filing_submission, filing, filing_meta)

                case "putBackOff":
                    put_back_off.process(business, filing, filing_submission, filing_meta)

                case "putBackOn":
                    put_back_on.process(business, filing, filing_submission, filing_meta)

                case "registrarsNotation":
                    registrars_notation.process(filing_submission, filing, filing_meta)

                case "registrarsOrder":
                    registrars_order.process(filing_submission, filing, filing_meta)

                case "registration":
                    business, filing_submission, filing_meta = \
                        registration.process(business,
                                             filing_submission.json,
                                             filing_submission,
                                             filing_meta,
                                             flags)

                case "restoration":
                    restoration.process(business, filing, filing_submission, filing_meta)

                case "specialResolution":
                    special_resolution.process(business, filing, filing_submission)

                case "transition":
                    filing_submission = transition.process(business, filing_submission, filing, filing_meta)

                case "transparencyRegister":
                    transparency_register.process(business, filing_submission, filing)

        # Add the current transaction
        filing_submission.transaction_id = transaction_id

        if business:
            business.last_modified = filing_submission.completion_date
            db.session.add(business)

        filing_submission._meta_data = json.loads(  # pylint: disable=W0212
            json.dumps(filing_meta.asjson, default=json_serial)
        )

        db.session.add(filing_submission)
        db.session.commit()

        if filing_submission.filing_type in [
            FilingTypes.AMALGAMATIONAPPLICATION,
            FilingTypes.CONTINUATIONIN,
            # code says corps conversion creates a new business (not sure: why?, in use (not implemented in UI)?)
            FilingTypes.CONVERSION,
            FilingTypes.INCORPORATIONAPPLICATION,
            FilingTypes.REGISTRATION
        ]:
            # update business id for new business
            filing_submission.business_id = business.id
            db.session.add(filing_submission)
            db.session.commit()

            # update affiliation for new business
            if filing_submission.filing_type != FilingTypes.CONVERSION:
                business_profile.update_affiliation(business, filing_submission, flags)

            name_request.consume_nr(business, filing_submission, flags=flags)
            business_profile.update_business_profile(business, filing_submission, flags=flags)
            PublishEvent.publish_mras_email(current_app, business, filing_submission)
        elif not flags.is_on("enable-sandbox"):
            for filing_type in filing_meta.legal_filings:
                if filing_type in [
                    FilingTypes.AMALGAMATIONOUT,
                    FilingTypes.ALTERATION,
                    FilingTypes.CHANGEOFREGISTRATION,
                    FilingTypes.CONTINUATIONOUT,
                    FilingTypes.CORRECTION,
                    FilingTypes.DISSOLUTION,
                    FilingTypes.PUTBACKON,
                    FilingTypes.RESTORATION
                ]:
                    business_profile.update_entity(business, filing_type)

                if filing_type in [
                    FilingTypes.ALTERATION,
                    FilingTypes.CHANGEOFREGISTRATION,
                    FilingTypes.CHANGEOFNAME,
                    FilingTypes.CORRECTION,
                    FilingTypes.RESTORATION,
                ]:
                    name_request.consume_nr(business,
                                            filing_submission,
                                            filing_type=filing_type,
                                            flags=flags)
                    if filing_type != FilingTypes.CHANGEOFNAME:
                        business_profile.update_business_profile(business,
                                                                    filing_submission,
                                                                    filing_type,
                                                                    flags=flags)

        if not flags.is_on("enable-sandbox"):
            PublishEvent.publish_email_message(current_app, business, filing_submission, filing_submission.status)

        PublishEvent.publish_event(current_app, business, filing_submission)
