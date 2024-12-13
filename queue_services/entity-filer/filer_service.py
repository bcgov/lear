#!/usr/bin/env python
# -*- coding: utf-8 -*-

# Copyright © 2019 Province of British Columbia
#
# Licensed under the Apache License, Version 2.0 (the 'License');
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an 'AS IS' BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
"""s2i based launch script to run the service."""
import asyncio
import os

from entity_queue_common.service_utils import logger

from entity_filer.resources import register_endpoints
from entity_filer.worker import APP_CONFIG, FLASK_APP, cb_subscription_handler, flags, qsm


if __name__ == '__main__':
    # This flag is added specifically for the sandbox environment.
    with FLASK_APP.app_context():
        flag_on = flags.is_on("enable-sandbox")
    logger.debug(f"enable-sandbox flag on: {flag_on}")

    if flag_on:
        # GCP Queue
        register_endpoints(FLASK_APP)
        server_port = os.environ.get("PORT", "8080")
        FLASK_APP.run(debug=False, port=server_port, host="0.0.0.0")
    else:
        # NATS Queue
        event_loop = asyncio.get_event_loop()
        event_loop.run_until_complete(qsm.run(loop=event_loop,
                                            config=APP_CONFIG,
                                            callback=cb_subscription_handler))
        try:
            event_loop.run_forever()
        finally:
            event_loop.close()
