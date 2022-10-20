# Copyright © 2022 Province of British Columbia
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
"""This module contains all of the Legal Filing specific processors.

Processors hold the logic to communicate with CRA.
"""
from pathlib import Path

import requests
from entity_queue_common.service import QueueServiceManager
from entity_queue_common.service_utils import logger
from flask import current_app
from jinja2 import Template
from legal_api.models import RequestTracker


qsm = QueueServiceManager()  # pylint: disable=invalid-name

program_type_code = {
    'SP': '113',
    'GP': '114'
}

business_type_code = {
    'SP': '01',
    'GP': '02'
}

business_sub_type_code = {
    'SP': '01',
    'GP': '99'
}

document_sub_type = {
    RequestTracker.RequestType.CHANGE_PARTY: '102',
    RequestTracker.RequestType.CHANGE_NAME: '103',
    RequestTracker.RequestType.CHANGE_DELIVERY_ADDRESS: '107',
    RequestTracker.RequestType.CHANGE_MAILING_ADDRESS: '108'
}


def build_input_xml(template_name, data):
    """Build input XML."""
    template = Path(
        f'{current_app.config.get("TEMPLATE_PATH")}/{template_name}.xml'
    ).read_text()
    jnja_template = Template(template, autoescape=True)
    return jnja_template.render(data)


def request_bn_hub(input_xml):
    """Get request to BN Hub."""
    try:
        url = current_app.config.get('BN_HUB_API_URL')
        username = current_app.config.get('BN_HUB_CLIENT_ID')
        secret = current_app.config.get('BN_HUB_CLIENT_SECRET')
        response = requests.get(url=url, params={'inputXML': input_xml}, auth=(username, secret))
        return response.status_code, response.text
    except requests.exceptions.RequestException as err:
        logger.error(err, exc_info=True)
        return None, str(err)


async def publish_event(payload: dict, subject: str):  # pylint: disable=redefined-outer-name
    """Publish the message onto the NATS subject."""
    await qsm.service.publish(subject, payload)
