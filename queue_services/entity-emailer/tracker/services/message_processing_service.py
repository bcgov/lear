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


from datetime import datetime
from typing import Optional

from tracker.models import MessageProcessing


class MessageProcessingService:  # pylint: disable=too-many-public-methods
    """Provides service for MessageProcessing related functionality"""

    @staticmethod
    def create_message(message_id: str,
                       identifier: str,
                       message_type: str,
                       status: MessageProcessing.Status,
                       message_json: str,
                       create_date: datetime,
                       last_update: datetime):
        msg = MessageProcessing()
        msg.message_id = message_id
        msg.identifier = identifier
        msg.message_type = message_type
        msg.status = status.value
        msg.message_json = message_json
        msg.create_date = create_date
        msg.last_update = last_update
        msg.save()

        return msg


    @staticmethod
    def update_message_status(msg: MessageProcessing, status: MessageProcessing.Status):
        msg.status = status.value
        msg.last_update = datetime.utcnow()
        msg.save()

        return msg


    @staticmethod
    def update_message_status_by_message_id(message_id: str, status: MessageProcessing.Status):
        msg = MessageProcessingService.find_message_by_message_id(message_id)
        msg.status = status.value
        msg.save()

        return msg


    @staticmethod
    def find_message_by_message_id(message_id: str) -> Optional[MessageProcessing]:
        """Find MessageProcessing by message_id."""
        msg = MessageProcessing.find_message_by_message_id(message_id=message_id)

        return msg


