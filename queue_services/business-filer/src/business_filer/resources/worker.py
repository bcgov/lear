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
"""The unique worker functionality for this service is contained here."""
import re
import traceback
from dataclasses import dataclass
from http import HTTPStatus
from typing import Optional

from flask import Blueprint, current_app, request
from gcp_queue import SimpleCloudEvent

from business_filer.services import gcp_queue, verify_gcp_jwt
from business_filer.services.filer import process_filing
from business_filer.common.filing_message import get_filing_message


bp = Blueprint('worker', __name__)


@bp.route('/', methods=('POST',))
def worker():
    """Process the incoming cloud event.

    Flow
    --------
    1. Get cloud event
    2. Get filing message information
    3. Process filing
    Decisions on returning a 2xx or failing value to
    the Queue should be noted here:
    - Empty or garbaled messages are knocked off the Q
    - Filings that cannot be processed are knocked off the Q
    """
    if not request.data:
        current_app.logger.debug('No incoming raw msg.')
        return {}, HTTPStatus.OK

    if msg := verify_gcp_jwt(request):
        current_app.logger.info(msg)
        return {}, HTTPStatus.FORBIDDEN

    current_app.logger.info(f'Incoming raw msg: {str(request.data)}')

    # 1. Get cloud event
    # ##
    if not (ce := gcp_queue.get_simple_cloud_event(request,
                                                   wrapped=True)) \
            and not isinstance(ce, SimpleCloudEvent):
        #
        # Decision here is to return a 200,
        # so the event is removed from the Queue
        current_app.logger.debug(f'ignoring message, raw payload: {str(ce)}')
        return {}, HTTPStatus.OK
    current_app.logger.info(f'received ce: {str(ce)}')

    # 2. Get filing_message information
    # ##
    if not (filing_message := get_filing_message(ce)):
        # no filing_message info, take off Q
        current_app.logger.debug(f'no filing_message info in: {ce}')
        return {'message': 'no filing info in cloud event'}, HTTPStatus.OK
    current_app.logger.info(f'Incoming filing_message: {filing_message}')

    # 3. Process Filing
    # ##
    try:
        process_filing(filing_message)
    except Exception as err:  # pylint: disable=broad-exception-caught
        current_app.logger.error(f'Error processing filing {filing_message}: {err}')
        current_app.logger.debug(traceback.format_exc())
        return {'error': f'Unable to process filing: {filing_message}'}, HTTPStatus.INTERNAL_SERVER_ERROR

    # Completed
    current_app.logger.info(f'completed ce: {str(ce)}')
    return {}, HTTPStatus.OK
