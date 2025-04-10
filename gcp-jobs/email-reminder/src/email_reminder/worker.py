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
"""Email Reminder job worker functionality is contained here."""
import uuid
from datetime import UTC, datetime

import requests
from flask import current_app
from simple_cloudevent import SimpleCloudEvent, to_queue_message
from flask_sqlalchemy.pagination import Pagination
from sqlalchemy.sql.expression import text

from business_account.AccountService import AccountService
from business_model.models import Business, Filing, db
from email_reminder.services import gcp_queue
from email_reminder.services.flags import Flags


def send_email(business_id: int, ar_fee: str, ar_year: str):
    """Put bn email messages on the queue for all businesses with new tax ids."""
    try:
        topic = current_app.config["BUSINESS_EMAILER_TOPIC"]
        ce = SimpleCloudEvent(
            id=str(uuid.uuid4()),
            source="emailReminderJob",
            subject="filing",
            time=datetime.now(UTC),
            type="bc.registry.reminder.annualReport",
            data = {
                'email': {
                    'businessId': business_id,
                    'type': 'annualReport',
                    'option': 'reminder',
                    'arFee': ar_fee,
                    'arYear': ar_year
                }
            }
        )
        print(f'publish {business_id}')
        gcp_queue.publish(topic, to_queue_message(ce))
    except Exception as err:
        current_app.logger.error(f'Queue Error: Failed to place ar reminder email for business id {business_id} on Queue with error:{err}')
        raise err


def get_ar_fee(legal_type: str, token: str) -> str:
    """Get AR fee."""
    current_app.logger.debug(f'token: {token}')
    current_app.logger.debug(f'legal_type: {legal_type}')
    fee_url = current_app.config.get('PAYMENT_SVC_FEES_URL')
    current_app.logger.debug(f'fee_url: {fee_url}')
    filing_type_code = Filing.FILINGS['annualReport']['codes'].get(legal_type, None)
    ar_filing = Filing.FILINGS['annualReport']
    current_app.logger.debug(f'Filing.FILINGS: {ar_filing}')
    current_app.logger.debug(f'filing_type_code: {filing_type_code}')
    fee_url = ''.join([fee_url, '/', legal_type, '/', filing_type_code])
    current_app.logger.debug(f'fee_url: {fee_url}')
    res = requests.get(url=fee_url,
                       headers={
                           'Content-Type': 'application/json',
                           'Authorization': 'Bearer ' + token,
                           'App-Name': 'email-reminder-job'},
                       timeout=30)
    current_app.logger.debug(f'res: {res}')
    current_app.logger.debug(f'res: {res.json()}')
    ar_fee = res.json().get('filingFees')
    current_app.logger.debug(f'ar_fee: {ar_fee}')
    return str(ar_fee)


def get_businesses(legal_types: list) -> Pagination:
    """Get businesses to send AR reminder today."""
    where_clause = text(
        'CASE WHEN last_ar_reminder_year IS NULL THEN date(founding_date)' +
        ' ELSE date(founding_date)' +
        ' + MAKE_INTERVAL(YEARS := last_ar_reminder_year - EXTRACT(YEAR FROM founding_date)::INTEGER)' +
        " END  + interval '1 year' <= CURRENT_DATE")
    return db.session.query(Business).filter(
        Business.legal_type.in_(legal_types),
        Business.send_ar_ind == True,
        Business.state == Business.State.ACTIVE,
        # restoration_expiry_date will have a value for limitedRestoration and limitedRestorationExtension
        Business.restoration_expiry_date == None,
        where_clause
    ).order_by(Business.id).paginate(per_page=20)


def find_and_send_ar_reminder():
    """Find business to send annual report reminder."""
    try:
        legal_types = [Business.LegalTypes.BCOMP.value,
                       Business.LegalTypes.BCOMP_CONTINUE_IN.value,
                       Business.LegalTypes.CONTINUE_IN.value,
                       Business.LegalTypes.ULC_CONTINUE_IN.value,
                       Business.LegalTypes.CCC_CONTINUE_IN.value,]  # entity types to send ar reminder

        if Flags.is_on('enable-bc-ccc-ulc-email-reminder'):
            legal_types.extend(
                [Business.LegalTypes.COMP.value,
                 Business.LegalTypes.BC_CCC.value,
                 Business.LegalTypes.BC_ULC_COMPANY.value]
            )

        ar_fees = {}

        # get token
        token = AccountService.get_bearer_token()
        for legal_type in legal_types:
            ar_fees[legal_type] = get_ar_fee(legal_type, token)

        current_app.logger.debug('Getting businesses to send AR reminder today')
        pagination = get_businesses(legal_types)
        while pagination.items:
            current_app.logger.debug('Processing businesses to send AR reminder')
            for item in pagination.items:
                business: Business = item  # setting new variable for the typing
                ar_year = (business.last_ar_reminder_year
                           if business.last_ar_reminder_year else business.founding_date.year) + 1
                try:
                    send_email(business.id, ar_fees[business.legal_type], str(ar_year))
                    current_app.logger.debug(f'Successfully queued ar reminder for business id {business.id}.')
                    business.last_ar_reminder_year = ar_year
                    business.save()
                except Exception as err:
                    # log error for human review
                    current_app.logger.error('Error sending email reminder for %s', business.identifier)

            if pagination.next_num:
                pagination = pagination.next()
            else:
                break

    except Exception as err:
        current_app.logger.error(err)


def send_outstanding_bcomps_ar_reminder():
    """Find outstanding bcomps to send annual report reminder."""
    try:
        # get token
        token = AccountService.get_bearer_token()
        ar_fee = get_ar_fee(Business.LegalTypes.BCOMP.value, token)

        current_app.logger.debug('Getting outstanding bcomps to send AR reminder')
        where_clause = text(
            'CASE WHEN last_ar_date IS NULL THEN date(founding_date) ELSE date(last_ar_date) END' +
            " <= CURRENT_DATE - interval '1 year'")
        businesses = db.session.query(Business).filter(
            Business.legal_type == Business.LegalTypes.BCOMP.value,
            where_clause
        ).all()
        current_app.logger.debug('Processing outstanding bcomps to send AR reminder')

        for business in businesses:
            ar_year = (business.last_ar_year if business.last_ar_year else business.founding_date.year) + 1

            send_email(business.id, ar_fee, str(ar_year))
            current_app.logger.debug(f'Successfully queued ar reminder for business id {business.id} for year {ar_year}.')

    except Exception as err:
        current_app.logger.error(err)


def run():
    """Run the email reminder worker."""
    if current_app.config.get('SEND_OUTSTANDING_BCOMPS') == 'send.outstanding.bcomps':
        send_outstanding_bcomps_ar_reminder()
    else:
        find_and_send_ar_reminder()

