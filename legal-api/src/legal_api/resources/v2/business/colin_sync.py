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
from legal_api.models import (
    AmalgamatingBusiness,
    Amalgamation,
    BatchProcessing,
    Business,
    Filing,
    PartyRole,
    UserRoles,
    db,
)
from legal_api.models.colin_event_id import ColinEventId
from legal_api.services.business_details_version import VersionedBusinessDetailsService
from legal_api.utils.auth import jwt
from legal_api.utils.legislation_datetime import LegislationDatetime

from .bp import bp


@bp.route('/internal/filings', methods=['GET'])
@cross_origin(origin='*')
@jwt.has_one_of_roles([UserRoles.colin])
def get_completed_filings_for_colin():
    """Get filings by status formatted in json."""
    filings = []

    page = int(request.args.get('page', 1))
    limit = int(request.args.get('limit', 20))
    pending_filings = Filing.get_completed_filings_for_colin(page, limit)
    for filing in pending_filings.get('filings'):
        filing_json = filing.filing_json
        business = Business.find_by_internal_id(filing.business_id)

        if filing_json and filing.filing_type != 'lear_epoch' and \
                (filing.filing_type != 'correction' or business.legal_type != Business.LegalTypes.COOP.value):
            filing_json['filingId'] = filing.id
            filing_json['filing']['header']['date'] = filing.filing_date.isoformat()
            filing_json['filing']['header']['learEffectiveDate'] = filing.effective_date.isoformat()
            if not filing_json['filing'].get('business'):
                # ideally filing should have transaction_id once completed.
                # found some filing in DEV (with missing transaction_id), adding this check to avoid exception
                if filing.transaction_id:
                    business_revision = VersionedBusinessDetailsService.get_business_revision_obj(
                        filing.transaction_id, business.id)
                    filing_json['filing']['business'] = VersionedBusinessDetailsService.business_revision_json(
                        business_revision, business.json())
                else:
                    filing_json['filing']['business'] = business.json()
            elif not filing_json['filing']['business'].get('legalName'):
                filing_json['filing']['business']['legalName'] = business.legal_name

            if filing.filing_type == 'correction':
                colin_ids = \
                    ColinEventId.get_by_filing_id(filing_json['filing']['correction']['correctedFilingId'])
                if not colin_ids:
                    continue
                filing_json['filing']['correction']['correctedFilingColinId'] = colin_ids[0]  # should only be 1
            elif (filing.filing_type == 'amalgamationApplication' and
                    filing_json['filing']['amalgamationApplication']['type'] in [
                        Amalgamation.AmalgamationTypes.horizontal.name,
                        Amalgamation.AmalgamationTypes.vertical.name]):
                try:
                    set_from_primary_or_holding_business_data(filing_json, filing)
                except Exception as ex:  # noqa: B902
                    current_app.logger.info(ex)
                    continue  # do not break this function because of one filing
            elif (filing.filing_type == 'dissolution' and
                  filing.filing_sub_type == 'involuntary'):
                batch_processings = BatchProcessing.find_by(filing_id=filing.id)
                if not batch_processings:
                    continue  # skip filing for missing batch processing info
                filing_json['filing']['dissolution']['metaData'] = batch_processings[0].meta_data

            filings.append(filing_json)
    return jsonify({
        'filings': filings,
        'page': page,
        'limit': limit,
        'pages': pending_filings.get('pages'),
        'total': pending_filings.get('total')
    }), HTTPStatus.OK


@bp.route('/internal/batch_processings', methods=['GET'])
@cross_origin(origin='*')
@jwt.has_one_of_roles([UserRoles.colin])
def get_eligible_batch_processings_for_colin():
    """Get batch processings by status formatted in json."""
    batch_processings = []

    page = int(request.args.get('page', 1))
    limit = int(request.args.get('limit', 20))
    pending_batch_processings = BatchProcessing.get_eligible_batch_processings_for_colin(page, limit)
    for batch_processing in pending_batch_processings.get('batchProcessings'):
        business = Business.find_by_internal_id(batch_processing.business_id)

        batch_processings.append({
            **batch_processing.json,
            'businessLegalType': business.legal_type
        })

    return jsonify({
        'batchProcessings': batch_processings,
        'page': page,
        'limit': limit,
        'pages': pending_batch_processings.get('pages'),
        'total': pending_batch_processings.get('total')
    }), HTTPStatus.OK


def set_from_primary_or_holding_business_data(filing_json, filing: Filing):
    """Set legal_name, director, office and shares from holding/primary business."""
    amalgamation_filing = filing_json['filing']['amalgamationApplication']
    primary_or_holding = next(x for x in amalgamation_filing['amalgamatingBusinesses']
                              if x['role'] in [AmalgamatingBusiness.Role.holding.name,
                                               AmalgamatingBusiness.Role.primary.name])

    ting_business = Business.find_by_identifier(primary_or_holding['identifier'])
    primary_or_holding_business = VersionedBusinessDetailsService.get_business_revision_obj(filing.transaction_id,
                                                                                            ting_business.id)

    amalgamation_filing['nameRequest']['legalName'] = primary_or_holding_business.legal_name

    _set_parties(primary_or_holding_business, filing, amalgamation_filing)
    _set_offices(primary_or_holding_business, amalgamation_filing, filing.transaction_id)
    _set_shares(primary_or_holding_business, amalgamation_filing, filing.transaction_id)


def _set_parties(primary_or_holding_business, filing, amalgamation_filing):
    parties = []
    parties_version = VersionedBusinessDetailsService.get_party_role_revision(filing.transaction_id,
                                                                              primary_or_holding_business.id,
                                                                              role=PartyRole.RoleTypes.DIRECTOR.value)
    # copy director
    for director_json in parties_version:
        director_json['roles'] = [{
            'roleType': 'Director',
            'appointmentDate': LegislationDatetime.format_as_legislation_date(filing.effective_date)
        }]
        parties.append(director_json)

    # copy completing party from filing json
    for party_info in amalgamation_filing.get('parties'):
        if comp_party_role := next((x for x in party_info.get('roles')
                                    if x['roleType'].lower() == 'completing party'), None):
            party_info['roles'] = [comp_party_role]  # override roles to have only completing party
            parties.append(party_info)
            break
    amalgamation_filing['parties'] = parties


def _set_offices(primary_or_holding_business, amalgamation_filing, transaction_id):
    # copy offices
    amalgamation_filing['offices'] = VersionedBusinessDetailsService.get_office_revision(transaction_id,
                                                                                         primary_or_holding_business.id)


def _set_shares(primary_or_holding_business, amalgamation_filing, transaction_id):
    # copy shares
    share_classes = VersionedBusinessDetailsService.get_share_class_revision(transaction_id,
                                                                             primary_or_holding_business.id)
    amalgamation_filing['shareStructure'] = {'shareClasses': share_classes}
    business_dates = [item.resolution_date.isoformat() for item in primary_or_holding_business.resolutions]
    if business_dates:
        amalgamation_filing['shareStructure']['resolutionDates'] = business_dates


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


@bp.route('/internal/batch_processings/<int:batch_processing_id>', methods=['PATCH'])
@cross_origin(origin='*')
@jwt.has_one_of_roles([UserRoles.colin])
def update_batch_processing_colin_id(batch_processing_id):
    """Patch the colin_event_id for a batch processing."""
    # check authorization
    try:
        json_input = request.get_json()
        if not json_input:
            return None, None, {
                'message': f'No batch processing json data in body of patch for {batch_processing_id}.'
            }, HTTPStatus.BAD_REQUEST

        colin_ids = json_input['colinIds']
        batch_processing = BatchProcessing.find_by_id(batch_processing_id)
        if not batch_processing_id:
            return {'message': f'{batch_processing_id} no batch processings found'}, HTTPStatus.NOT_FOUND
        for colin_id in colin_ids:
            try:
                colin_event_id_obj = ColinEventId()
                colin_event_id_obj.colin_event_id = colin_id
                colin_event_id_obj.batch_processing_step = batch_processing.step
                batch_processing.colin_event_ids.append(colin_event_id_obj)
                batch_processing.save()
            except BusinessException as err:
                current_app.logger.Error(
                    f'Error adding colin event id {colin_id} to batch processing with id {batch_processing_id}'
                )
                return None, None, {'message': err.error}, err.status_code

        return jsonify(batch_processing.json), HTTPStatus.ACCEPTED
    except Exception as err:
        current_app.logger.Error(f'Error patching colin event id for batch processing with id {batch_processing}')
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
