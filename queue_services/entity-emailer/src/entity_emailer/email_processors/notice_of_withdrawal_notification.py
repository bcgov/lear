# Copyright © 2025 Province of British Columbia
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
"""Email processing rules and actions for Notice of Withdrawal notifications"""
import base64
import re
from http import HTTPStatus
from pathlib import Path

import requests
from entity_queue_common.service_utils import logger
from flask import current_app
from jinja2 import Template
from legal_api.models import Business, Filing

from entity_emailer.email_processors import get_filing_info, get_recipient_from_auth, substitute_template_parts


def process(email_info: dict, token: str) -> dict:
    """Build the email for Notice of Withdrawal notification"""
    logger.debug('notice_of_withdrawal_notification: %s', email_info)
    # get template and fill in parts
    filing_type, status = email_info['type'], email_info['option']
    # do not process if NoW filing status is not COMPLETED
    if status is not Filing.Status.COMPLETED:
        return {}
    # get template variables from filing
    filing, business_json, leg_tmz_filing_date, leg_tmz_effective_date = get_filing_info(email_info['filingId'])
    