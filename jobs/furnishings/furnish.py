# Copyright © 2021 Province of British Columbia
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
"""Furnishings job."""
import asyncio

from legal_api.services.queue import QueueService

from furnishings.worker import create_app, run


if __name__ == '__main__':
    application = create_app()
    try:
        event_loop = asyncio.get_event_loop()
        queue_service = QueueService(app=application, loop=event_loop)
        event_loop.run_until_complete(run(application, queue_service))
    except Exception as err:  # pylint: disable=broad-except; Catching all errors from the frameworks
        application.logger.error(err)  # pylint: disable=no-member
        raise err
