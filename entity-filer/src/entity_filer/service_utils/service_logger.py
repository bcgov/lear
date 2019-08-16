# Copyright © 2019 Province of British Columbia
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
"""Setup logging for the service.

# TODO: logging format should be moved to an external config file
"""
import logging
import os

import sentry_sdk
from sentry_sdk.integrations.logging import LoggingIntegration


def before_breadcrumb(crumb, hint):  # pylint: disable=unused-argument; callback function signature from sentry
    """Render nothing for the breadcrumb history."""
    return None


# Configure Sentry
SENTRY_DSN = os.getenv('SENTRY_DSN', None)
if SENTRY_DSN:

    SENTRY_LOGGING = LoggingIntegration(
        event_level=logging.ERROR  # Send errors as events
    )
    sentry_sdk.init(
        dsn=SENTRY_DSN,
        integrations=[SENTRY_LOGGING],
        before_breadcrumb=before_breadcrumb
    )

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s,%(msecs)d-%(name)s-%(levelname)s > %(module)s:%(filename)s:%(lineno)d-%(funcName)s:%(message)s',
    datefmt='%H:%M:%S',
)
logging.getLogger('asyncio').setLevel(logging.DEBUG)

logger = logging.getLogger('asyncio')
