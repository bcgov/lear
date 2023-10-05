# Copyright © 2023 Province of British Columbia
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
import os
import uuid
from http import HTTPStatus
from typing import Dict

from flask import Blueprint
from flask import request

from entity_filer import db
# from legal_api.core import Filing as FilingCore
from business_model import LegalEntity, Filing
# from legal_api.services.bootstrap import AccountService
from entity_filer.utils.datetime import datetime
from sqlalchemy.exc import OperationalError

from entity_filer.services.logging import structured_log
from entity_filer.exceptions import BusinessException
from entity_filer import config
from entity_filer.filing_meta import FilingMeta, json_serial
from entity_filer.filing_processors import (
    admin_freeze,
    alteration,
    annual_report,
    change_of_address,
    change_of_directors,
    change_of_name,
    change_of_registration,
    consent_continuation_out,
    continuation_out,
    conversion,
    correction,
    court_order,
    dissolution,
    incorporation_filing,
    put_back_on,
    registrars_notation,
    registrars_order,
    registration,
    restoration,
    special_resolution,
    transition,
)
from entity_filer.filing_processors.filing_components import name_request


bp = Blueprint("worker", __name__)


@bp.route("/", methods=("POST",))
def worker():

    structured_log(request, "INFO", f"Incoming raw msg: {request.data}")

    # 1. Get cloud event
    # ##
    # if not (ce := queue.get_simple_cloud_event(request)):
        #
        # Decision here is to return a 200,
        # so the event is removed from the Queue
        # return {}, HTTPStatus.OK
    
    # try:
    #     print('Received raw message seq:%s, data=  %s', msg.sequence, msg.data.decode())
    #     filing_msg = json.loads(msg.data.decode('utf-8'))
    #     print('Extracted filing msg: %s', filing_msg)
    #     await process_filing(filing_msg, FLASK_APP)
    # except OperationalError as err:
    #     print('Queue Blocked - Database Issue: %s', json.dumps(filing_msg), exc_info=True)
    #     raise err  # We don't want to handle the error, as a DB down would drain the queue
    # except FilingException as err:
    #     print('Queue Error - cannot find filing: %s'
    #                  '\n\nThis message has been put back on the queue for reprocessing.',
    #                  json.dumps(filing_msg), exc_info=True)
    #     raise err  # we don't want to handle the error, so that the message gets put back on the queue
    # except (BusinessException, Exception):  # pylint: disable=broad-except
    #     # Catch Exception so that any error is still caught and the message is removed from the queue
    #     print('Queue Error:' + json.dumps(filing_msg), level='error')
    #     print('Queue Error: %s', json.dumps(filing_msg), exc_info=True)

    # structured_log(request, "INFO", f"received ce: {str(ce)}")
    return {}, 500




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


async def publish_event(business: LegalEntity, filing: Filing):
    """Publish the filing message onto the NATS filing subject."""
    try:
        payload = {
            'specversion': '1.x-wip',
            'type': 'bc.registry.business.' + filing.filing_type,
            'source': ''.join([
                # APP_CONFIG.LEGAL_API_URL,
                '/business/',
                business.identifier,
                '/filing/',
                str(filing.id)]),
            'id': str(uuid.uuid4()),
            'time': datetime.utcnow().isoformat(),
            'datacontenttype': 'application/json',
            'identifier': business.identifier,
            'data': {
                'filing': {
                    'header': {'filingId': filing.id,
                               'effectiveDate': filing.effective_date.isoformat()
                               },
                    'business': {'identifier': business.identifier},
                    'legalFilings': get_filing_types(filing.filing_json)
                }
            }
        }
        if filing.temp_reg:
            payload['tempidentifier'] = filing.temp_reg
        # subject = APP_CONFIG.ENTITY_EVENT_PUBLISH_OPTIONS['subject']
        # await qsm.service.publish(subject, payload)
    except Exception as err:  # pylint: disable=broad-except; we don't want to fail out the filing, so ignore all.
        print('Queue Publish Event Error: filing.id=' + str(filing.id) + str(err), level='error')
        print('Queue Publish Event Error: filing.id=%s', filing.id, exc_info=True)


def process_filing(filing_msg: Dict):  # pylint: disable=too-many-branches,too-many-statements
    """Render the filings contained in the submission.

    Start the migration to using core/Filing
    """
    if not (filing_submission := Filing.find_by_id(filing_msg['filing']['id'])):
        raise BusinessException

    if filing_submission.status == Filing.Status.COMPLETED:
        print('QueueFiler: Attempting to reprocess business.id=%s, filing.id=%s filing=%s',
                        filing_submission.legal_entity_id, filing_submission.id, filing_msg)
        return None, None

    # if legal_filings := filing_submission.legal_filings():

    #     business = LegalEntity.find_by_internal_id(filing_submission.legal_entity_id)

    #     filing_meta = FilingMeta(application_date=filing_submission.effective_date,
    #                                 legal_filings=[item for sublist in
    #                                             [list(x.keys()) for x in legal_filings]
    #                                             for item in sublist])

    #     for filing_type, filing in legal_filings.items():
    #         # if not(filing_type := 'alteration'):
    #         #     break

    worker_filing_json = filing_submission.tech_correction_json \
                         or filing_submission.filing_json
    # worker_filing_json = filing_submission.filing_json
    
    legal_filings = [x for x in 
                        [x for x in worker_filing_json.get('filing',{}).keys()]
                    if Filing.FILINGS.get(x) is not None]
    
    business = LegalEntity.find_by_internal_id(filing_submission.legal_entity_id)
    filing_meta = FilingMeta(application_date=filing_submission.effective_date,
                legal_filings=legal_filings
                )

    # for filing_type, filing in filing_submission.filing_json['filing'].items():
    for filing_type, filing in worker_filing_json['filing'].items():
        
        if not Filing.FILINGS.get(filing_type):
            continue

        match filing_type:
            case 'adminFreeze':
                admin_freeze.process(business, {filing_type: filing}, filing_submission, filing_meta)

            case 'alteration':
                alteration.process(business, filing_submission, {filing_type: filing}, filing_meta)
            
            case 'annualReport':
                annual_report.process(business, {filing_type: filing}, filing_meta)
            
            case 'changeOfAddress':
               change_of_address.process(business, {filing_type: filing}, filing_meta)

            case 'changeOfDirectors':
                filing['colinIds'] = filing_submission.colin_event_ids
                change_of_directors.process(business, {filing_type: filing}, filing_meta)
            
            case 'changeOfName':
                change_of_name.process(business, {filing_type: filing}, filing_meta)

            case 'changeOfRegistration':
                change_of_registration.process(business, filing_submission, {filing_type: filing}, filing_meta)
            
            case 'consentContinuationOut':
                consent_continuation_out.process(business, filing_submission, {filing_type: filing}, filing_meta)

            case 'continuationOut':
               continuation_out.process(business, filing_submission, {filing_type: filing}, filing_meta)
            
            case 'conversion':
                business, filing_submission = conversion.process(
                                business,
                                filing_submission.json,
                                filing_submission,
                                filing_meta)

            case 'correction':
                filing_submission = correction.process(filing_submission, {filing_type: filing}, filing_meta, business)

            case 'courtOrder':
                court_order.process(business, filing_submission, {filing_type: filing}, filing_meta)

            case 'dissolution':
                dissolution.process(business, {filing_type: filing}, filing_submission, filing_meta)

            case 'incorporationApplication':
                business, filing_submission, filing_meta = incorporation_filing.process(business,
                                                                                        filing_submission.json,
                                                                                        filing_submission,
                                                                                        filing_meta)

            case 'putBackOn':
                put_back_on.process(business, {filing_type: filing}, filing_submission, filing_meta)

            case 'registrarsNotation':
                registrars_notation.process(filing_submission, {filing_type: filing}, filing_meta)

            case 'registrarsOrder':
                registrars_order.process(filing_submission, {filing_type: filing}, filing_meta)

            case 'registration':
                business, filing_submission, filing_meta = registration.process(business,
                                                                                filing_submission.json,
                                                                                filing_submission,
                                                                                filing_meta)

            case 'restoration':
                restoration.process(business, {filing_type: filing}, filing_submission, filing_meta)

            case 'specialResolution':
                special_resolution.process(business, {filing_type: filing}, filing_submission)

            case 'transition':
                filing_submission = transition.process(business, filing_submission, {filing_type: filing}, filing_meta)

            case _ :
                raise Exception()

    business_type = business.entity_type if business else filing_submission['business']['legal_type']
    filing_submission.set_processed(business_type)

    filing_submission._meta_data = json.loads(  # pylint: disable=W0212
        json.dumps(filing_meta.asjson, default=json_serial)
    )

    db.session.add(business)
    db.session.add(filing_submission)
    db.session.commit()

    # post filing changes to other services
    if any('dissolution' in x for x in legal_filings):
        # TODO 
        pass
        # AccountService.update_entity(
        #     business_registration=business.identifier,
        #     business_name=business.legal_name,
        #     corp_type_code=business.legal_type,
        #     state=LegalEntity.State.HISTORICAL.name
        # )

    if any('putBackOn' in x for x in legal_filings):
        # TODO 
        pass
        # AccountService.update_entity(
        #     business_registration=business.identifier,
        #     business_name=business.legal_name,
        #     corp_type_code=business.legal_type,
        #     state=LegalEntity.State.ACTIVE.name
        # )

    if filing_submission.filing_type == filing_submission.FilingTypes.RESTORATION:
        # TODO 
        pass
        # restoration.post_process(business, filing_submission)
        # AccountService.update_entity(
        #     business_registration=business.identifier,
        #     business_name=business.legal_name,
        #     corp_type_code=business.legal_type,
        #     state=LegalEntity.State.ACTIVE.name
        # )

    if any('alteration' in x for x in legal_filings):
        # TODO 
        pass
        # alteration.post_process(business, filing_submission, is_correction)
        # AccountService.update_entity(
        #     business_registration=business.identifier,
        #     business_name=business.legal_name,
        #     corp_type_code=business.legal_type
        # )

    if any('changeOfRegistration' in x for x in legal_filings):
        # TODO 
        pass
        # change_of_registration.post_process(business, filing_submission)
        # AccountService.update_entity(
        #     business_registration=business.identifier,
        #     business_name=business.legal_name,
        #     corp_type_code=business.legal_type
        # )

    if business.entity_type in ['SP', 'GP', 'BC', 'BEN', 'CC', 'ULC', 'CP'] and \
            any('correction' in x for x in legal_filings):
        # TODO 
        pass
        # correction.post_process(business, filing_submission)
        # AccountService.update_entity(
        #     business_registration=business.identifier,
        #     business_name=business.legal_name,
        #     corp_type_code=business.legal_type
        # )

    if any('incorporationApplication' in x for x in legal_filings):
        filing_submission.legal_entity_id = business.id
        db.session.add(filing_submission)
        db.session.commit()
        # TODO 
        pass
        # incorporation_filing.update_affiliation(business, filing_submission)
        # name_request.consume_nr(business, filing_submission)
        # incorporation_filing.post_process(business, filing_submission)
        # try:
        #     await publish_email_message(
        #         qsm, APP_CONFIG.EMAIL_PUBLISH_OPTIONS['subject'], filing_submission, 'mras')
        # except Exception as err:  # pylint: disable=broad-except, unused-variable # noqa F841;
        #     # mark any failure for human review
        #     print(
        #         f'Queue Error: Failed to place email for filing:{filing_submission.id}'
        #         f'on Queue with error:{err}',
        #         level='error'
        #     )

    if any('registration' in x for x in legal_filings):
        filing_submission.business_id = business.id
        db.session.add(filing_submission)
        db.session.commit()
        # TODO 
        pass
        # registration.update_affiliation(business, filing_submission)
        # name_request.consume_nr(business, filing_submission, 'registration')
        # registration.post_process(business, filing_submission)

    if any('changeOfName' in x for x in legal_filings):
        change_of_name.post_process(business, filing_submission)

    if any('conversion' in x for x in legal_filings):
        filing_submission.business_id = business.id
        db.session.add(filing_submission)
        db.session.commit()
        conversion.post_process(business, filing_submission)

    # try:
    #     await publish_email_message(
    #         qsm, APP_CONFIG.EMAIL_PUBLISH_OPTIONS['subject'], filing_submission, filing_submission.status)
    # except Exception as err:  # pylint: disable=broad-except, unused-variable # noqa F841;
    #     # mark any failure for human review
    #     print(
    #         f'Queue Error: Failed to place email for filing:{filing_submission.id}'
    #         f'on Queue with error:{err}',
    #         level='error'
    #     )

    # try:
    #     await publish_event(business, filing_submission)
    # except Exception as err:  # pylint: disable=broad-except, unused-variable # noqa F841;
    #     # mark any failure for human review
    #     print(err)
    #     print(
    #         f'Queue Error: Failed to publish event for filing:{filing_submission.id}'
    #         f'on Queue with error:{err}',
    #         level='error'
    #     )
