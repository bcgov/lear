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

The entry-point is the **cb_subscription_handler**

The design and flow leverage a few constraints that are placed upon it
by NATS Streaming and using AWAIT on the default loop.
- NATS streaming queues require one message to be processed at a time.
- AWAIT on the default loop effectively runs synchronously

If these constraints change, the use of Flask-SQLAlchemy would need to change.
Flask-SQLAlchemy currently allows the base model to be changed, or reworking
the model to a standalone SQLAlchemy usage with an async engine would need
to be pursued.
"""
import json
import os
import uuid
from typing import Dict

import nats
from entity_queue_common.messages import publish_email_message
from entity_queue_common.service import QueueServiceManager
from entity_queue_common.service_utils import FilingException, QueueException
from flask import Flask, current_app
from gcp_queue import SimpleCloudEvent, to_queue_message
from legal_api.core import Filing as FilingCore
from legal_api.models import Business, Filing, db
from legal_api.models.db import VersioningProxy, init_db
from legal_api.services import Flags
from legal_api.utils.datetime import datetime, timezone
from sentry_sdk import capture_message
from sqlalchemy.exc import OperationalError

from entity_filer import config
from entity_filer.filing_meta import FilingMeta, json_serial
from entity_filer.filing_processors import (
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
from entity_filer.filing_processors.filing_components import business_profile, name_request
from entity_filer.services import gcp_queue


qsm = QueueServiceManager()  # pylint: disable=invalid-name
flags = Flags()  # pylint: disable=invalid-name
APP_CONFIG = config.get_named_config(os.getenv('DEPLOYMENT_ENV', 'production'))
FLASK_APP = Flask(__name__)
FLASK_APP.config.from_object(APP_CONFIG)
init_db(FLASK_APP)
gcp_queue.init_app(FLASK_APP)

if FLASK_APP.config.get('LD_SDK_KEY', None):
    flags.init_app(FLASK_APP)


def get_filing_types(legal_filings: dict):
    """Get the filing type fee codes for the filing.

    Returns: {
        list: a list of filing types.
    }
    """
    filing_types = []
    for k in legal_filings['filing'].keys():
        if Filing.FILINGS.get(k, None):
            filing_types.append(k)
    return filing_types


async def publish_event(business: Business, filing: Filing):
    """Publish the filing message onto the NATS filing subject."""
    temp_reg = filing.temp_reg
    if filing.filing_type == FilingCore.FilingTypes.NOTICEOFWITHDRAWAL and filing.withdrawn_filing:
        current_app.logger.debug('publish_event - notice of withdrawal filing: %s, withdrawan_filing: %s',
                                 filing, filing.withdrawn_filing)
        temp_reg = filing.withdrawn_filing.temp_reg
    business_identifier = business.identifier if business else temp_reg

    try:
        payload = {
            'specversion': '1.x-wip',
            'type': 'bc.registry.business.' + filing.filing_type,
            'source': ''.join([
                APP_CONFIG.LEGAL_API_URL,
                '/business/',
                business_identifier,
                '/filing/',
                str(filing.id)]),
            'id': str(uuid.uuid4()),
            'time': datetime.utcnow().isoformat(),
            'datacontenttype': 'application/json',
            'identifier': business_identifier,
            'data': {
                'filing': {
                    'header': {'filingId': filing.id,
                               'effectiveDate': filing.effective_date.isoformat()
                               },
                    'business': {'identifier': business_identifier},
                    'legalFilings': get_filing_types(filing.filing_json)
                }
            }
        }
        if temp_reg:
            payload['tempidentifier'] = temp_reg

        subject = APP_CONFIG.ENTITY_EVENT_PUBLISH_OPTIONS['subject']
        await qsm.service.publish(subject, payload)
    except Exception as err:  # pylint: disable=broad-except; we don't want to fail out the filing, so ignore all.
        capture_message('Queue Publish Event Error: filing.id=' + str(filing.id) + str(err), level='error')
        current_app.logger.error('Queue Publish Event Error: filing.id=%s', filing.id, exc_info=True)


def publish_gcp_queue_event(business: Business, filing: Filing):
    """Publish the filing message onto the GCP-QUEUE filing subject."""
    temp_reg = filing.temp_reg
    if filing.filing_type == FilingCore.FilingTypes.NOTICEOFWITHDRAWAL and filing.withdrawn_filing:
        current_app.logger.debug('publish_event - notice of withdrawal filing: %s, withdrawan_filing: %s',
                                 filing, filing.withdrawn_filing)
        temp_reg = filing.withdrawn_filing.temp_reg
    business_identifier = business.identifier if business else temp_reg

    try:
        subject = APP_CONFIG.BUSINESS_EVENTS_TOPIC
        data = {
            'filing': {
                'header': {
                    'filingId': filing.id,
                    'effectiveDate': filing.effective_date.isoformat()
                },
                'business': {'identifier': business_identifier},
                'legalFilings': get_filing_types(filing.filing_json)
            },
            'identifier': business_identifier
        }
        if temp_reg:
            data['tempidentifier'] = temp_reg

        ce = SimpleCloudEvent(
            id=str(uuid.uuid4()),
            source=''.join([
                APP_CONFIG.LEGAL_API_URL,
                '/business/',
                business_identifier,
                '/filing/',
                str(filing.id)]),
            subject=subject,
            time=datetime.now(timezone.utc),
            type='bc.registry.business.' + filing.filing_type,
            data=data
        )

        gcp_queue.publish(subject, to_queue_message(ce))

    except Exception as err:  # pylint: disable=broad-except; we don't want to fail out the filing, so ignore all.
        capture_message('Queue Publish Event Error: filing.id=' + str(filing.id) + str(err), level='error')
        current_app.logger.error('Queue Publish Event Error: filing.id=%s', filing.id, exc_info=True)


async def publish_mras_email(filing: Filing):
    """Publish MRAS email message onto the NATS emailer subject."""
    if flags.is_on('enable-sandbox'):
        current_app.logger.info('Skip publishing MRAS email')
        return

    if filing.filing_type in [
        FilingCore.FilingTypes.AMALGAMATIONAPPLICATION,
        FilingCore.FilingTypes.CONTINUATIONIN,
        FilingCore.FilingTypes.INCORPORATIONAPPLICATION
    ]:
        try:
            await publish_email_message(
                qsm, APP_CONFIG.EMAIL_PUBLISH_OPTIONS['subject'], filing, 'mras')
        except Exception as err:  # pylint: disable=broad-except, unused-variable # noqa F841;
            # mark any failure for human review
            capture_message(
                f'Queue Error: Failed to place MRAS email for filing:{filing.id}'
                f'on Queue with error:{err}',
                level='error'
            )


async def process_filing(filing_msg: Dict,  # pylint: disable=too-many-branches,too-many-statements,too-many-locals
                         flask_app: Flask):
    """Render the filings contained in the submission.

    Start the migration to using core/Filing
    """
    if not flask_app:
        raise QueueException('Flask App not available.')

    with flask_app.app_context():
        # filing_submission = Filing.find_by_id(filing_msg['filing']['id'])
        filing_core_submission = FilingCore.find_by_id(filing_msg['filing']['id'])

        if not filing_core_submission:
            raise QueueException('No filing found.')

        filing_submission = filing_core_submission.storage

        if filing_core_submission.status in [Filing.Status.COMPLETED, Filing.Status.WITHDRAWN]:
            current_app.logger.warning('QueueFiler: Attempting to reprocess business.id=%s, filing.id=%s filing=%s',
                                       filing_submission.business_id, filing_submission.id, filing_msg)
            return None, None
        if filing_submission.withdrawal_pending:
            current_app.logger.warning('QueueFiler: NoW pending for this filing business.id=%s, filing.id=%s filing=%s',
                                       filing_submission.business_id, filing_submission.id, filing_msg)
            raise QueueException

        # convenience flag to set that the envelope is a correction
        is_correction = filing_core_submission.filing_type == FilingCore.FilingTypes.CORRECTION

        # pylint: disable=too-many-nested-blocks, disable=too-many-function-args;
        if legal_filings := filing_core_submission.legal_filings():
            transaction_id = VersioningProxy.get_transaction_id(db.session())

            business = Business.find_by_internal_id(filing_submission.business_id)

            filing_meta = FilingMeta(application_date=filing_submission.effective_date,
                                     legal_filings=[item for sublist in
                                                    [list(x.keys()) for x in legal_filings]
                                                    for item in sublist])
            if is_correction:
                filing_meta.correction = {}

            for filing in legal_filings:
                if filing.get('alteration'):
                    alteration.process(business, filing_submission, filing, filing_meta, is_correction)

                elif filing.get('annualReport'):
                    flag_on = flags.is_on('enable-involuntary-dissolution')
                    current_app.logger.debug('enable-involuntary-dissolution flag on: %s', flag_on)
                    annual_report.process(business, filing, filing_meta, flag_on)

                elif filing.get('changeOfAddress'):
                    flag_on = flags.is_on('enable-involuntary-dissolution')
                    change_of_address.process(business, filing, filing_meta, flag_on)

                elif filing.get('changeOfDirectors'):
                    change_of_directors.process(business, filing_submission, filing_meta)

                elif filing.get('changeOfName'):
                    change_of_name.process(business, filing, filing_meta)

                elif filing.get('dissolution'):
                    flag_on = flags.is_on('enable-involuntary-dissolution')
                    dissolution.process(business, filing, filing_submission, filing_meta, flag_on)

                elif filing.get('incorporationApplication'):
                    business, filing_submission, filing_meta = incorporation_filing.process(business,
                                                                                            filing_core_submission.json,
                                                                                            filing_submission,
                                                                                            filing_meta,
                                                                                            flags)

                elif filing.get('registration'):
                    business, filing_submission, filing_meta = registration.process(business,
                                                                                    filing_core_submission.json,
                                                                                    filing_submission,
                                                                                    filing_meta,
                                                                                    flags)

                elif filing.get('conversion'):
                    business, filing_submission = conversion.process(business,
                                                                     filing_core_submission.json,
                                                                     filing_submission,
                                                                     filing_meta)

                elif filing.get('courtOrder'):
                    court_order.process(business, filing_submission, filing, filing_meta)

                elif filing.get('registrarsNotation'):
                    registrars_notation.process(filing_submission, filing, filing_meta)

                elif filing.get('registrarsOrder'):
                    registrars_order.process(filing_submission, filing, filing_meta)

                elif filing.get('correction'):
                    filing_submission = correction.process(filing_submission, filing, filing_meta, business)

                elif filing.get('transition'):
                    filing_submission = transition.process(business, filing_submission, filing, filing_meta)

                elif filing.get('changeOfRegistration'):
                    change_of_registration.process(business, filing_submission, filing, filing_meta)

                elif filing.get('putBackOff'):
                    put_back_off.process(business, filing, filing_submission, filing_meta)

                elif filing.get('putBackOn'):
                    put_back_on.process(business, filing, filing_submission, filing_meta)

                elif filing.get('restoration'):
                    restoration.process(business, filing, filing_submission, filing_meta)

                elif filing.get('adminFreeze'):
                    admin_freeze.process(business, filing, filing_submission, filing_meta)

                elif filing.get('consentAmalgamationOut'):
                    consent_amalgamation_out.process(business, filing_submission, filing, filing_meta)

                elif filing.get('amalgamationOut'):
                    amalgamation_out.process(business, filing_submission, filing, filing_meta)

                elif filing.get('consentContinuationOut'):
                    consent_continuation_out.process(business, filing_submission, filing, filing_meta)

                elif filing.get('continuationOut'):
                    continuation_out.process(business, filing_submission, filing, filing_meta)

                elif filing.get('agmLocationChange'):
                    agm_location_change.process(filing, filing_meta)

                elif filing.get('agmExtension'):
                    agm_extension.process(filing, filing_meta)

                elif filing.get('noticeOfWithdrawal'):
                    notice_of_withdrawal.process(filing_submission, filing, filing_meta)

                elif filing.get('amalgamationApplication'):
                    business, filing_submission, filing_meta = amalgamation_application.process(
                        business,
                        filing_core_submission.json,
                        filing_submission,
                        filing_meta,
                        flags)

                elif filing.get('continuationIn'):
                    business, filing_submission, filing_meta = continuation_in.process(
                        business,
                        filing_core_submission.json,
                        filing_submission,
                        filing_meta,
                        flags)

                elif filing.get('transparencyRegister'):
                    transparency_register.process(business, filing_submission, filing_core_submission.json)

                elif filing.get('appointReceiver'):
                    appoint_receiver.process(business, filing, filing_submission, filing_meta)

                elif filing.get('ceaseReceiver'):
                    cease_receiver.process(business, filing, filing_submission, filing_meta)

                if filing.get('specialResolution'):
                    special_resolution.process(business, filing, filing_submission)

            filing_submission.transaction_id = transaction_id

            business_type = business.legal_type if business \
                else filing_submission.filing_json.get('filing', {}).get('business', {}).get('legalType')
            filing_submission.set_processed(business_type)
            if business:
                business.last_modified = filing_submission.completion_date
                db.session.add(business)

            filing_submission._meta_data = json.loads(  # pylint: disable=W0212
                json.dumps(filing_meta.asjson, default=json_serial)
            )

            db.session.add(filing_submission)
            db.session.commit()

            if filing_core_submission.filing_type in [
                FilingCore.FilingTypes.AMALGAMATIONAPPLICATION,
                FilingCore.FilingTypes.CONTINUATIONIN,
                # code says corps conversion creates a new business (not sure: why?, in use (not implemented in UI)?)
                FilingCore.FilingTypes.CONVERSION,
                FilingCore.FilingTypes.INCORPORATIONAPPLICATION,
                FilingCore.FilingTypes.REGISTRATION
            ]:
                # update business id for new business
                filing_submission.business_id = business.id
                db.session.add(filing_submission)
                db.session.commit()

                # update affiliation for new business
                if filing_core_submission.filing_type != FilingCore.FilingTypes.CONVERSION:
                    business_profile.update_affiliation(business, filing_submission, flags)

                name_request.consume_nr(business, filing_submission, flags=flags)
                business_profile.update_business_profile(business, filing_submission, flags=flags)
                await publish_mras_email(filing_submission)
            else:
                if not flags.is_on('enable-sandbox'):
                    for filing_type in filing_meta.legal_filings:
                        if filing_type in [
                            FilingCore.FilingTypes.AMALGAMATIONOUT,
                            FilingCore.FilingTypes.ALTERATION,
                            FilingCore.FilingTypes.CHANGEOFREGISTRATION,
                            FilingCore.FilingTypes.CONTINUATIONOUT,
                            FilingCore.FilingTypes.CORRECTION,
                            FilingCore.FilingTypes.DISSOLUTION,
                            FilingCore.FilingTypes.PUTBACKON,
                            FilingCore.FilingTypes.RESTORATION
                        ]:
                            business_profile.update_entity(business, filing_type)

                        if filing_type in [
                            FilingCore.FilingTypes.ALTERATION,
                            FilingCore.FilingTypes.CHANGEOFREGISTRATION,
                            FilingCore.FilingTypes.CHANGEOFNAME,
                            FilingCore.FilingTypes.CORRECTION,
                            FilingCore.FilingTypes.RESTORATION,
                        ]:
                            name_request.consume_nr(business,
                                                    filing_submission,
                                                    filing_type=filing_type,
                                                    flags=flags)
                            if filing_type != FilingCore.FilingTypes.CHANGEOFNAME:
                                business_profile.update_business_profile(business,
                                                                         filing_submission,
                                                                         filing_type,
                                                                         flags=flags)

            # TODO: remove NATS publishing once GCP migration is complete
            if not flags.is_on('enable-sandbox'):
                try:
                    await publish_email_message(
                        qsm, APP_CONFIG.EMAIL_PUBLISH_OPTIONS['subject'], filing_submission, filing_submission.status)
                except Exception as err:  # pylint: disable=broad-except, unused-variable # noqa F841;
                    # mark any failure for human review
                    capture_message(
                        f'Queue Error: Failed to place email for filing:{filing_submission.id}'
                        f'on Queue with error:{err}',
                        level='error'
                    )

                try:
                    await publish_event(business, filing_submission)
                except Exception as err:  # pylint: disable=broad-except, unused-variable # noqa F841;
                    # mark any failure for human review
                    print(err)
                    capture_message(
                        f'Queue Error: Failed to publish event for filing:{filing_submission.id}'
                        f'on Queue with error:{err}',
                        level='error'
                    )

            else:
                try:
                    publish_gcp_queue_event(business, filing_submission)
                except Exception as err:  # pylint: disable=broad-except, unused-variable # noqa F841;
                    # mark any failure for human review
                    print(err)
                    capture_message(
                        f'Queue Error: Failed to publish event for filing:{filing_submission.id}'
                        f'on Queue with error:{err}',
                        level='error'
                    )


async def cb_subscription_handler(msg: nats.aio.client.Msg):
    """Use Callback to process Queue Msg objects."""
    try:
        current_app.logger.info('Received raw message seq:%s, data=  %s', msg.sequence, msg.data.decode())
        filing_msg = json.loads(msg.data.decode('utf-8'))
        current_app.logger.debug('Extracted filing msg: %s', filing_msg)
        await process_filing(filing_msg, FLASK_APP)
    except OperationalError as err:
        current_app.logger.error('Queue Blocked - Database Issue: %s', json.dumps(filing_msg), exc_info=True)
        raise err  # We don't want to handle the error, as a DB down would drain the queue
    except FilingException as err:
        current_app.logger.error('Queue Error - cannot find filing: %s'
                                 '\n\nThis message has been put back on the queue for reprocessing.',
                                 json.dumps(filing_msg), exc_info=True)
        raise err  # we don't want to handle the error, so that the message gets put back on the queue
    except (QueueException, Exception):  # pylint: disable=broad-except
        # Catch Exception so that any error is still caught and the message is removed from the queue
        capture_message('Queue Error:' + json.dumps(filing_msg), level='error')
        current_app.logger.error('Queue Error: %s', json.dumps(filing_msg), exc_info=True)
