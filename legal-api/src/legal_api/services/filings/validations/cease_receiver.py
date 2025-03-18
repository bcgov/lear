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
"""Validation for the Cease Receiver filing."""
from http import HTTPStatus
from typing import Dict, Optional

from flask_babel import _ as babel  # noqa: N813, I004, I001, I003

from legal_api.errors import Error
from legal_api.models import Business


def validate(business: Business, cease_receiver: Dict) -> Optional[Error]:
    """Validate the Cease Receiver filing."""
    if not business or not cease_receiver:
        return Error(HTTPStatus.BAD_REQUEST, [{'error': babel('A valid business and filing are required.')}])
    msg = []
    msg.append(validate_party(cease_receiver))

    if msg:
        return Error(HTTPStatus.BAD_REQUEST, msg)
    return None


def validate_party(filing: Dict) -> list:
    """Validate party."""
    msg = []
    parties = filing['filing']['ceaseReceiver']['parties']

    if len(parties) == 0:
        msg.append({'error': 'Must have an Receiver.', 'path': '/filing/ceaseReceiver/parties'})

    return msg
