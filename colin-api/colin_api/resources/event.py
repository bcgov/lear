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
"""Event info endpoint for colin db."""
from flask import current_app, jsonify
from flask_restplus import Resource, cors

from colin_api.resources.business import API
from colin_api.resources.db import DB
from colin_api.utils.util import cors_preflight


@cors_preflight('GET, POST')
@API.route('/event/<string:corp_type>/<string:event_id>')
class EventInfo(Resource):
    """Meta information about the overall service."""

    @staticmethod
    @cors.crossdomain(origin='*')
    def get(corp_type, event_id):
        """Return all event_ids of the given corp_type above the given event_id."""
        try:
            cursor = DB.connection.cursor()
            cursor.execute(
                """
                select event.event_id, corp_num, filing.filing_typ_cd
                from event
                join filing on event.event_id = filing.event_id
                where event.event_id > :max_event_id and corp_num like :corp_type
                """,
                max_event_id=event_id,
                corp_type=corp_type + '%'
            )
            event_info = cursor.fetchall()
            event_list = []
            for event in event_info:
                event = dict(zip([x[0].lower() for x in cursor.description], event))
                event_list.append(event)
            return jsonify({'events': event_list})

        except Exception as err:  # pylint: disable=broad-except; want to catch all errors
            current_app.logger.error(err.with_traceback(None))
            return jsonify(
                {'message': 'Error when trying to retrieve events from COLIN'}), 500
