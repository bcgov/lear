# Copyright © 2020 Province of British Columbia
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

"""This provides the service for getting business details as of a filing."""
# pylint: disable=singleton-comparison ; pylint does not recognize sqlalchemy ==


from business_model.utils import datetime  # noqa: I001
from typing import Optional

from tracker.models import MessageProcessing


class MessageProcessingService:  # pylint: disable=too-many-public-methods
    """Provides service for MessageProcessing related functionality"""

    @staticmethod
    def create_message(message_id: str,
                       source: str,
                       identifier: str,
                       message_type: str,
                       status: MessageProcessing.Status,
                       message_json: str,
                       seen_count: int,
                       last_error: str):
        dt_now = datetime.datetime.utcnow()
        msg = MessageProcessing()
        msg.message_id = message_id
        msg.source = source
        msg.identifier = identifier
        msg.message_type = message_type
        msg.status = status.value
        msg.message_json = message_json
        msg.message_seen_count = seen_count
        msg.last_error = last_error
        msg.create_date = dt_now
        msg.last_update = dt_now
        msg.save()

        return msg


    @staticmethod
    def update_message_status(msg: MessageProcessing,
                              status: MessageProcessing.Status,
                              error_details: None,
                              increment_seen_count=False):
        msg.status = status.value
        if error_details:
            msg.last_error = error_details
        if increment_seen_count:
            msg.message_seen_count += 1
        msg.last_update = datetime.datetime.utcnow()
        msg.save()

        return msg


    @staticmethod
    def update_message_status_by_message_id(message_id: str, status: MessageProcessing.Status,
                                            increment_seen_count=False):
        msg = MessageProcessingService.find_message_by_message_id(message_id)
        msg.status = status.value
        if increment_seen_count:
            msg.message_seen_count += 1
        msg.last_update = datetime.datetime.utcnow()
        msg.save()

        return msg


    @staticmethod
    def update_message_last_error(msg: MessageProcessing,
                                  error_details: str,
                                  increment_seen_count=False):
        msg.last_error = error_details
        if increment_seen_count:
            msg.message_seen_count += 1
        msg.last_update = datetime.datetime.utcnow()
        msg.save()

        return msg


    @staticmethod
    def find_message_by_message_id(message_id: str) -> Optional[MessageProcessing]:
        """Find MessageProcessing by message_id."""
        msg = MessageProcessing.find_message_by_message_id(message_id=message_id)

        return msg


    @staticmethod
    def find_message_by_source_and_message_id(source: str, message_id: str) -> Optional[MessageProcessing]:
        """Find MessageProcessing by source and message_id."""
        msg = MessageProcessing.find_message_by_source_and_message_id(source=source, message_id=message_id)

        return msg
