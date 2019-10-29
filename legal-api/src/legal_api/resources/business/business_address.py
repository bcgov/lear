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
"""Searching on a business entity addresses.

Retrieve the Addresses for the entity.
"""
from http import HTTPStatus

from flask import jsonify, request
from flask_restplus import Resource, cors

from legal_api.models import Address, Business, db
from legal_api.utils.util import cors_preflight

from .api_namespace import API
# noqa: I003; the multiple route decorators cause an erroneous error in line space counting


@cors_preflight('GET,')
@API.route('/<string:identifier>/addresses', methods=['GET', 'OPTIONS'])
@API.route('/<string:identifier>/addresses/<int:addresses_id>', methods=['GET', 'OPTIONS'])
class AddressResource(Resource):
    """Business Address service."""

    @staticmethod
    @cors.crossdomain(origin='*')
    def get(identifier, addresses_id=None):
        """Return a JSON of the addresses on file."""
        business = Business.find_by_identifier(identifier)

        if not business:
            return jsonify({'message': f'{identifier} not found'}), HTTPStatus.NOT_FOUND

        address_type = request.args.get('addressType', None)
        if address_type and address_type not in Address.JSON_ADDRESS_TYPES:
            return jsonify({'message': f'{address_type} not a valid address type'}), HTTPStatus.BAD_REQUEST

        if addresses_id or address_type:
            addresses, msg, code = AddressResource._get_address(business, addresses_id, address_type)
            return jsonify(addresses or msg), code

        # return all active addresses
        rv = {}
        officelist = business.offices.all()
        if officelist:
            for i in officelist:
                rv[i.office_type] = {}
                for address in i.addresses:
                    rv[i.office_type][f'{address.address_type}Address'] = address.json
        else:
            mailing = business.mailing_address.one_or_none()
            if mailing:
                rv[Address.JSON_MAILING] = mailing.json
            delivery = business.delivery_address.one_or_none()
            if delivery:
                rv[Address.JSON_DELIVERY] = delivery.json
            if not rv:
                return jsonify({'message': f'{identifier} address not found'}), HTTPStatus.NOT_FOUND
        return jsonify(rv)

    @staticmethod
    def _get_address(business, addresses_id=None, address_type=None):
        # find by ID
        addresses = None
        if addresses_id:
            rv = db.session.query(Business, Address). \
                filter(Business.id == Address.business_id).\
                filter(Business.identifier == business.identifier).\
                filter(Address.id == addresses_id).\
                one_or_none()
            if rv:
                _address_type = Address.JSON_MAILING \
                    if rv[1].address_type == Address.MAILING else Address.JSON_DELIVERY
                addresses = {_address_type: rv[1].json}

        # find by address type
        if address_type:
            if address_type.lower() == Address.JSON_MAILING.lower():
                _address_type = Address.JSON_MAILING
                address = business.mailing_address.one_or_none()
            else:
                _address_type = Address.JSON_DELIVERY
                address = business.delivery_address.one_or_none()
            if address:
                addresses = {_address_type: address.json}

        if not addresses:
            return None, {'message': f'{business.identifier} address not found'}, HTTPStatus.NOT_FOUND

        return addresses, None, HTTPStatus.OK
