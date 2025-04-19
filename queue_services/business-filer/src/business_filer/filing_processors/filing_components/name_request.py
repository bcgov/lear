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
"""Actions related to the name requests of a business."""
import json
from http import HTTPStatus

import requests

from business_filer.exceptions import QueueException
from flask import current_app
from business_model.models import Business, Filing, RegistrationBootstrap

from business_filer.services import AccountService, Flags
# from legal_api.services.utils import get_str


def consume_nr(business: Business, filing: Filing, filing_type: str = None, flags: Flags = None):
    """Update the nr to a consumed state."""
    return Exception
    # TODO: Fix this
    # try:
    #     if flags.is_on('enable-sandbox'):
    #         current_app.logger.info('Skip consuming NR')
    #         return

    #     filing_type = filing_type if filing_type else filing.filing_type
    #     # skip this if none (nrNumber will not be available for numbered company)
    #     if nr_num := get_str(filing.filing_json, f'/filing/{filing_type}/nameRequest/nrNumber'):

    #         namex_svc_url = current_app.config.get('NAMEX_API')
    #         token = AccountService.get_bearer_token()
    #         if flags and (flag_on := flags.is_on('namex-nro-decommissioned')):
    #             current_app.logger.debug('namex-nro-decommissioned flag: %s', flag_on)
    #             data = json.dumps({'state': 'CONSUMED', 'corpNum': business.identifier})
    #         else:
    #             data = json.dumps({'consume': {'corpNum': business.identifier}})

    #         rv = requests.patch(
    #             url=''.join([namex_svc_url, nr_num]),
    #             headers={**AccountService.CONTENT_TYPE_JSON,
    #                      'Authorization': AccountService.BEARER + token},
    #             data=data,
    #             timeout=AccountService.timeout
    #         )
    #         if not rv.status_code == HTTPStatus.OK:
    #             raise QueueException

    #         # remove the NR from the account
    #         if filing.temp_reg and (bootstrap := RegistrationBootstrap.find_by_identifier(filing.temp_reg)):
    #             AccountService.delete_affiliation(bootstrap.account, nr_num)
    # except KeyError:
    #     pass  # return
    # except Exception:  # pylint: disable=broad-except; note out any exception, but don't fail the call
    #     current_app.logger.info(f'Queue Error: Consume NR error for filing:{filing.id}', level='error')


def set_legal_name(business: Business, name_request_info: dict):
    """Set the legal_name in the business object."""
    if legal_name := name_request_info.get('legalName', None):
        business.legal_name = legal_name
