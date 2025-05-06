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
from flask_restx import Resource, cors

from colin_api.resources.business import API
from colin_api.resources.db import DB
from colin_api.utils.auth import COLIN_SVC_ROLE, jwt
from colin_api.utils.util import cors_preflight


@cors_preflight('GET, POST')
@API.route('/event/<string:corp_type>/<string:event_id>')
class EventInfo(Resource):
    """Meta information about the overall service."""

    @staticmethod
    @cors.crossdomain(origin='*')
    @jwt.requires_roles([COLIN_SVC_ROLE])
    def get(corp_type, event_id):
        """Return all event_ids of the corp_type that are greater than the given event_id."""
        querystring = """
            select event.event_id, corporation.corp_num, corporation.corp_typ_cd, filing.filing_typ_cd
            from event
            join filing on event.event_id = filing.event_id
            join corporation on EVENT.corp_num = corporation.corp_num
            where corporation.corp_typ_cd = :corp_type
            """
        try:
            cursor = DB.connection.cursor()
            if event_id != 'earliest':
                querystring += 'and event.event_id > :max_event_id '
                cursor.execute(querystring, max_event_id=event_id, corp_type=corp_type)
            else:
                querystring += "and event_timestmp > TO_DATE('2019-03-08', 'yyyy-mm-dd') order by event.event_id asc"
                cursor.execute(querystring, corp_type=corp_type)
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


@cors_preflight('GET')
@API.route('/event/corp_num/<string:corp_num>/<string:event_id>')
class CorpEventInfo(Resource):
    """Return a subset of event related info for a given corp num."""

    @staticmethod
    @cors.crossdomain(origin='*')
    @jwt.requires_roles([COLIN_SVC_ROLE])
    def get(corp_num, event_id):
        """Return all event_ids of the corp_type that are greater than the given event_id."""
        querystring = """
            select e.event_id, e.corp_num, f.filing_typ_cd
            from event e
                left join filing f on e.event_id = f.event_id
            where
                e.event_typ_cd in ('FILE', 'SYSDF') and
                e.corp_num = :corp_num and e.event_id > :event_id
            order by e.event_timestmp, e.event_id asc
            """
        try:
            cursor = DB.connection.cursor()
            cursor.execute(querystring, corp_num=corp_num, event_id=event_id)
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
