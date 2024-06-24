# Copyright © 2024 Province of British Columbia
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
"""Calls used by internal services jobs (update_colin_filings, update_legal_filings).

These endpoint are reqired as long as we sync to colin.
"""
from http import HTTPStatus

from flask import current_app, jsonify, request
from flask_cors import cross_origin

from legal_api.exceptions import BusinessException
from legal_api.models import Business, Filing, UserRoles, db
from legal_api.models.colin_event_id import ColinEventId
from legal_api.services.business_details_version import VersionedBusinessDetailsService
from legal_api.utils.auth import jwt

from .bp import bp


@bp.route('/internal/filings', methods=['GET'])
@bp.route('/internal/filings/<string:status>', methods=['GET'])
@cross_origin(origin='*')
@jwt.has_one_of_roles([UserRoles.colin])
def get_completed_filings_for_colin(status=None):
    """Get filings by status formatted in json."""
    pending_filings = []
    filings = []

    if status is None:
        pending_filings = Filing.get_completed_filings_for_colin()
        for filing in pending_filings:
            filing_json = filing.filing_json
            business = Business.find_by_internal_id(filing.business_id)
            business_revision = VersionedBusinessDetailsService.get_business_revision_obj(filing.transaction_id,
                                                                                          business.id)
            if filing_json and filing.filing_type != 'lear_epoch' and \
                    (filing.filing_type != 'correction' or business.legal_type != Business.LegalTypes.COOP.value):
                filing_json['filingId'] = filing.id
                filing_json['filing']['header']['learEffectiveDate'] = filing.effective_date.isoformat()
                if not filing_json['filing'].get('business'):
                    filing_json['filing']['business'] = VersionedBusinessDetailsService.business_revision_json(
                        business_revision, business.json())
                elif not filing_json['filing']['business'].get('legalName'):
                    filing_json['filing']['business']['legalName'] = business.legal_name
                if filing.filing_type == 'correction':
                    colin_ids = \
                        ColinEventId.get_by_filing_id(filing_json['filing']['correction']['correctedFilingId'])
                    if not colin_ids:
                        continue
                    filing_json['filing']['correction']['correctedFilingColinId'] = colin_ids[0]  # should only be 1
                filings.append(filing_json)
        return jsonify(filings), HTTPStatus.OK

    pending_filings = Filing.get_all_filings_by_status(status)
    for filing in pending_filings:
        filings.append(filing.json)
    return jsonify(filings), HTTPStatus.OK


@bp.route('/internal/filings/<int:filing_id>', methods=['PATCH'])
@cross_origin(origin='*')
@jwt.has_one_of_roles([UserRoles.colin])
def update_colin_id(filing_id):
    """Patch the colin_event_id for a filing."""
    # check authorization
    try:
        json_input = request.get_json()
        if not json_input:
            return None, None, {'message': f'No filing json data in body of patch for {filing_id}.'}, \
                HTTPStatus.BAD_REQUEST

        colin_ids = json_input['colinIds']
        filing = Filing.find_by_id(filing_id)
        if not filing:
            return {'message': f'{filing_id} no filings found'}, HTTPStatus.NOT_FOUND
        for colin_id in colin_ids:
            try:
                colin_event_id_obj = ColinEventId()
                colin_event_id_obj.colin_event_id = colin_id
                filing.colin_event_ids.append(colin_event_id_obj)
                filing.save()
            except BusinessException as err:
                current_app.logger.Error(f'Error adding colin event id {colin_id} to filing with id {filing_id}')
                return None, None, {'message': err.error}, err.status_code

        return jsonify(filing.json), HTTPStatus.ACCEPTED
    except Exception as err:
        current_app.logger.Error(f'Error patching colin event id for filing with id {filing_id}')
        raise err


@bp.route('/internal/filings/colin_id', methods=['GET'])
@bp.route('/internal/filings/colin_id/<int:colin_id>', methods=['GET'])
@cross_origin(origin='*')
@jwt.has_one_of_roles([UserRoles.colin])
def get_colin_event_id(colin_id=None):
    """Get the last colin id updated in legal."""
    try:
        if colin_id:
            colin_id_obj = ColinEventId.get_by_colin_id(colin_id)
            if not colin_id_obj:
                return {'message': 'No colin ids found'}, HTTPStatus.NOT_FOUND
            return {'colinId': colin_id_obj.colin_event_id}, HTTPStatus.OK
    except Exception as err:
        current_app.logger.Error(f'Failed to get last updated colin event id: {err}')
        raise err

    query = db.session.execute(
        """
        select last_event_id from colin_last_update
        order by id desc
        """
    )
    last_event_id = query.fetchone()
    if not last_event_id or not last_event_id[0]:
        return {'message': 'No colin ids found'}, HTTPStatus.NOT_FOUND

    return {'maxId': last_event_id[0]}, HTTPStatus.OK if request.method == 'GET' else HTTPStatus.CREATED


@bp.route('/internal/filings/colin_id/<int:colin_id>', methods=['POST'])
@cross_origin(origin='*')
@jwt.has_one_of_roles([UserRoles.colin])
def update_colin_event_id(colin_id):
    """Add a row to the colin_last_update table."""
    try:
        db.session.execute(
            f"""
            insert into colin_last_update (last_update, last_event_id)
            values (current_timestamp, {colin_id})
            """
        )
        db.session.commit()
        return get_colin_event_id()

    except Exception as err:  # pylint: disable=broad-except
        current_app.logger.error(f'Error updating colin_last_update table in legal db: {err}')
        return {'message: failed to update colin_last_update.', 500}


@bp.route('/internal/tax_ids', methods=['GET'])
@cross_origin(origin='*')
@jwt.has_one_of_roles([UserRoles.colin])
def get_all_identifiers_without_tax_id():
    """Return all identifiers with no tax_id set that are supposed to have a tax_id.

    Excludes COOPS because they do not get a tax id/business number.
    Excludes SP/GP we don't sync firms to colin, we use entity-bn to get tax id/business number from CRA.
    """
    identifiers = []
    bussinesses_no_taxid = Business.get_all_by_no_tax_id()
    for business in bussinesses_no_taxid:
        identifiers.append(business.identifier)
    return jsonify({'identifiers': identifiers}), HTTPStatus.OK


@bp.route('/internal/tax_ids', methods=['POST'])
@cross_origin(origin='*')
@jwt.has_one_of_roles([UserRoles.colin])
def set_tax_ids():
    """Set tax ids for businesses for given identifiers."""
    json_input = request.get_json()
    if not json_input:
        return ({'message': 'No identifiers in body of post.'}, HTTPStatus.BAD_REQUEST)

    for identifier in json_input.keys():
        # json input is a dict -> identifier: tax id
        business = Business.find_by_identifier(identifier)
        if business:
            business.tax_id = json_input[identifier]
            business.save()
        else:
            current_app.logger.error(f'Unable to update tax_id for business ({identifier}), which is missing in lear')
    return jsonify({'message': 'Successfully updated tax ids.'}), HTTPStatus.CREATED
