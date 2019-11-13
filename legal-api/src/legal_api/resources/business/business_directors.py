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
"""Retrieve the directors for the entity."""
from datetime import datetime
from http import HTTPStatus

from flask import jsonify, request
from flask_restplus import Resource, cors

from legal_api.models import Business, Director, db
from legal_api.utils.util import cors_preflight

from .api_namespace import API


@cors_preflight('GET,')
@API.route('/<string:identifier>/directors', methods=['GET', 'OPTIONS'])
@API.route('/<string:identifier>/directors/<int:director_id>', methods=['GET', 'OPTIONS'])
class DirectorResource(Resource):
    """Business Directors service."""

    @staticmethod
    @cors.crossdomain(origin='*')
    def get(identifier, director_id=None):
        """Return a JSON of the directors."""
        business = Business.find_by_identifier(identifier)

        if not business:
            return jsonify({'message': f'{identifier} not found'}), HTTPStatus.NOT_FOUND

        # return the matching director
        if director_id:
            director, msg, code = DirectorResource._get_director(business, director_id)
            return jsonify(director or msg), code

        # return all active directors as of date query param
        res = []
        end_date = datetime.utcnow().strptime(request.args.get('date'), '%Y-%m-%d').date()\
            if request.args.get('date') else datetime.utcnow().date()
        director_list = Director.get_active_directors(business.id, end_date)
        for director in director_list:
            director_json = director.json
            if business.legal_type == 'CP':
                del director_json['mailingAddress']
            res.append(director_json)

        return jsonify(directors=res)

    @staticmethod
    def _get_director(business, director_id=None):
        # find by ID
        director = None
        if director_id:
            rv = db.session.query(Business, Director). \
                filter(Business.id == Director.business_id). \
                filter(Business.identifier == business.identifier). \
                filter(Director.id == director_id). \
                one_or_none()
            if rv:
                director = {'director': rv[1].json}

        if not director:
            return None, {'message': f'{business.identifier} director not found'}, HTTPStatus.NOT_FOUND

        return director, None, HTTPStatus.OK
