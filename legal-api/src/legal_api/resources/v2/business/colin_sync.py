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
import copy
from http import HTTPStatus

from flask import current_app, jsonify, request
from flask_cors import cross_origin
from sqlalchemy import or_

from legal_api.exceptions import BusinessException
from legal_api.models import (
    Address,
    Alias,
    AmalgamatingBusiness,
    Amalgamation,
    BatchProcessing,
    Business,
    Filing,
    Office,
    Party,
    PartyRole,
    Resolution,
    ShareClass,
    ShareSeries,
    UserRoles,
    db,
)
from legal_api.models.colin_event_id import ColinEventId
from legal_api.models.db import VersioningProxy
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

    limit = int(request.args.get('limit', 20))
    offset = int(request.args.get('offset', 0))
    pending_filings = Filing.get_completed_filings_for_colin(limit, offset)
    for filing in pending_filings:
        business = Business.find_by_internal_id(filing.business_id)

        filing_json = copy.deepcopy(filing.filing_json)
        filing_json['filingId'] = filing.id
        filing_json['filing']['header']['source'] = Filing.Source.LEAR.value
        filing_json['filing']['header']['date'] = filing.filing_date.isoformat()
        filing_json['filing']['header']['learEffectiveDate'] = filing.effective_date.isoformat()
        filing_json['filing']['header']['isFutureEffective'] = filing.is_future_effective
        filing_json['filing']['header']['hideInLedger'] = filing.hide_in_ledger

        if not filing_json['filing'].get('business'):
            if filing.transaction_id:
                business_revision = VersionedBusinessDetailsService.get_business_revision_obj(filing, business.id)
                filing_json['filing']['business'] = VersionedBusinessDetailsService.business_revision_json(
                    business_revision, business.json())
            else:
                # should never happen unless its a test data created directly in db.
                # found some filing in DEV, adding this check to avoid exception
                filing_json['filing']['business'] = business.json()
        elif not filing_json['filing']['business'].get('legalName'):
            filing_json['filing']['business']['legalName'] = business.legal_name

        if filing.filing_type == 'correction' and business.legal_type != Business.LegalTypes.COOP.value:
            try:
                set_correction_flags(filing_json, filing)
            except Exception as ex:  # noqa: B902
                current_app.logger.error(f'correction: filingId={filing.id}, error: {str(ex)}')
                # to skip this filing and block subsequent filing from syncing in update-colin-filings
                filing_json['filing']['header']['name'] = None

        elif (filing.filing_type == 'amalgamationApplication' and
              filing_json['filing']['amalgamationApplication']['type'] in [
                  Amalgamation.AmalgamationTypes.horizontal.name,
                  Amalgamation.AmalgamationTypes.vertical.name]):
            try:
                set_from_primary_or_holding_business_data(filing_json, filing)
            except Exception as ex:  # noqa: B902
                current_app.logger.error(f'amalgamation: filingId={filing.id}, error: {str(ex)}')
                # to skip this filing and block subsequent filing from syncing in update-colin-filings
                filing_json['filing']['header']['name'] = None

        elif (filing.filing_type == 'dissolution' and filing.filing_sub_type == 'involuntary'):
            if batch_processings := BatchProcessing.find_by(filing_id=filing.id):
                filing_json['filing']['dissolution']['metaData'] = batch_processings[0].meta_data
            else:
                current_app.logger.error(f'dissolution: filingId={filing.id}, missing batch processing info')
                # to skip this filing and block subsequent filing from syncing in update-colin-filings
                filing_json['filing']['header']['name'] = None
        filings.append(filing_json)
    return jsonify({'filings': filings}), HTTPStatus.OK


def set_correction_flags(filing_json, filing: Filing):
    """Set what section changed in this correction."""
    if filing.meta_data.get('commentOnly', False):
        return

    if filing.meta_data.get('toLegalName'):
        filing_json['filing']['correction']['nameChanged'] = True

    if has_alias_changed(filing):
        filing_json['filing']['correction']['nameTranslationsChanged'] = True

    if has_office_changed(filing):
        filing_json['filing']['correction']['officeChanged'] = True

    if has_party_changed(filing):
        filing_json['filing']['correction']['partyChanged'] = True

    if has_resolution_changed(filing):
        filing_json['filing']['correction']['resolutionChanged'] = True

    if has_share_changed(filing):
        filing_json['filing']['correction']['shareChanged'] = True


def has_alias_changed(filing) -> bool:
    """Has alias changed in the given filing."""
    alias_version = VersioningProxy.version_class(db.session(), Alias)
    aliases_query = (db.session.query(alias_version)
                     .filter(or_(alias_version.transaction_id == filing.transaction_id,
                                 alias_version.end_transaction_id == filing.transaction_id))
                     .filter(alias_version.business_id == filing.business_id)
                     .exists())
    return db.session.query(aliases_query).scalar()


def has_office_changed(filing) -> bool:
    """Has office changed in the given filing."""
    offices = db.session.query(Office).filter(Office.business_id == filing.business_id).all()

    address_version = VersioningProxy.version_class(db.session(), Address)
    addresses_query = (db.session.query(address_version)
                       .filter(or_(address_version.transaction_id == filing.transaction_id,
                                   address_version.end_transaction_id == filing.transaction_id))
                       .filter(address_version.office_id.in_([office.id for office in offices]))
                       .filter(address_version.address_type.in_(['mailing', 'delivery']))
                       .exists())
    return db.session.query(addresses_query).scalar()


def has_party_changed(filing: Filing) -> bool:
    """Has party changed in the given filing."""
    party_role_version = VersioningProxy.version_class(db.session(), PartyRole)
    party_roles_query = (db.session.query(party_role_version)
                         .filter(or_(party_role_version.transaction_id == filing.transaction_id,
                                     party_role_version.end_transaction_id == filing.transaction_id))
                         .filter(party_role_version.business_id == filing.business_id)
                         .filter(party_role_version.role == PartyRole.RoleTypes.DIRECTOR.value)
                         .exists())
    if db.session.query(party_roles_query).scalar():  # Has new party added/deleted by setting cessation_date
        return True

    # Has existing party modified
    party_roles = VersionedBusinessDetailsService.get_party_role_revision(filing,
                                                                          filing.business_id,
                                                                          role=PartyRole.RoleTypes.DIRECTOR.value)

    party_version = VersioningProxy.version_class(db.session(), Party)
    for party_role in party_roles:
        parties_query = (db.session.query(party_version)
                         .filter(or_(party_version.transaction_id == filing.transaction_id,
                                     party_version.end_transaction_id == filing.transaction_id))
                         .filter(party_version.id == party_role['id'])
                         .exists())
        if db.session.query(parties_query).scalar():  # Modified party
            return True

        party = VersionedBusinessDetailsService.get_party_revision(filing, party_role['id'])
        address_version = VersioningProxy.version_class(db.session(), Address)
        # Has party delivery/mailing address modified
        address_query = (db.session.query(address_version)
                         .filter(or_(address_version.transaction_id == filing.transaction_id,
                                     address_version.end_transaction_id == filing.transaction_id))
                         .filter(address_version.id.in_([party.delivery_address_id, party.mailing_address_id]))
                         .exists())
        if db.session.query(address_query).scalar():  # Modified party delivery/mailing address
            return True

    return False


def has_resolution_changed(filing: Filing) -> bool:
    """Has resolution changed in the given filing."""
    resolution_version = VersioningProxy.version_class(db.session(), Resolution)
    resolution_query = (db.session.query(resolution_version)
                        .filter(or_(resolution_version.transaction_id == filing.transaction_id,
                                    resolution_version.end_transaction_id == filing.transaction_id))
                        .filter(resolution_version.business_id == filing.business_id)
                        .exists())
    return db.session.query(resolution_query).scalar()


def has_share_changed(filing: Filing) -> bool:
    """Has share changed in the given filing."""
    share_class_version = VersioningProxy.version_class(db.session(), ShareClass)
    share_class_query = (db.session.query(share_class_version)
                         .filter(or_(share_class_version.transaction_id == filing.transaction_id,
                                     share_class_version.end_transaction_id == filing.transaction_id))
                         .filter(share_class_version.business_id == filing.business_id)
                         .exists())
    if db.session.query(share_class_query).scalar():
        return True

    share_classes = VersionedBusinessDetailsService.get_share_class_revision(filing.transaction_id, filing.business_id)
    series_version = VersioningProxy.version_class(db.session(), ShareSeries)
    share_series_query = (db.session.query(series_version)
                          .filter(or_(series_version.transaction_id == filing.transaction_id,
                                      series_version.end_transaction_id == filing.transaction_id))
                          .filter(series_version.share_class_id.in_(
                              [share_class['id'] for share_class in share_classes]))
                          .exists())
    if db.session.query(share_series_query).scalar():
        return True

    return False


def set_from_primary_or_holding_business_data(filing_json, filing: Filing):
    """Set legal_name, director, office and shares from holding/primary business."""
    amalgamation_filing = filing_json['filing']['amalgamationApplication']
    primary_or_holding = next(x for x in amalgamation_filing['amalgamatingBusinesses']
                              if x['role'] in [AmalgamatingBusiness.Role.holding.name,
                                               AmalgamatingBusiness.Role.primary.name])

    ting_business = Business.find_by_identifier(primary_or_holding['identifier'])
    primary_or_holding_business = VersionedBusinessDetailsService.get_business_revision_obj(filing, ting_business.id)

    amalgamation_filing['nameRequest']['legalName'] = primary_or_holding_business.legal_name

    _set_parties(primary_or_holding_business, filing, amalgamation_filing)
    _set_offices(primary_or_holding_business, amalgamation_filing, filing.id, filing.transaction_id)
    _set_shares(primary_or_holding_business, amalgamation_filing, filing.transaction_id)


def _set_parties(primary_or_holding_business, filing, amalgamation_filing):
    parties = []
    parties_version = VersionedBusinessDetailsService.get_party_role_revision(filing,
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


def _set_offices(primary_or_holding_business, amalgamation_filing, filing_id, transaction_id):
    # copy offices
    amalgamation_filing['offices'] = VersionedBusinessDetailsService.get_office_revision(filing_id,
                                                                                         transaction_id,
                                                                                         primary_or_holding_business.id)


def _set_shares(primary_or_holding_business, amalgamation_filing, transaction_id):
    """Set shares from holding/primary business."""
    # Copy shares
    share_classes = VersionedBusinessDetailsService.get_share_class_revision(transaction_id,
                                                                             primary_or_holding_business.id)
    amalgamation_filing['shareStructure'] = {'shareClasses': share_classes}

    # Get resolution dates using versioned query
    resolution_version = VersioningProxy.version_class(db.session(), Resolution)
    resolutions_query = (
        db.session.query(resolution_version.resolution_date)
        .filter(resolution_version.transaction_id <= transaction_id)  # Get records valid at or before the transaction
        .filter(resolution_version.operation_type != 2)  # Exclude deleted records
        .filter(resolution_version.business_id == primary_or_holding_business.id)
        .filter(or_(
            resolution_version.end_transaction_id.is_(None),  # Records not yet ended
            resolution_version.end_transaction_id > transaction_id  # Records ended after our transaction
        ))
        .order_by(resolution_version.transaction_id)
        .all()
    )

    business_dates = [res.resolution_date.isoformat() for res in resolutions_query]
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


@bp.route('/internal/last-event-id/<identifier>', methods=['GET'])
@cross_origin(origin='*')
@jwt.has_one_of_roles([UserRoles.colin])
def get_last_event_id(identifier):
    """Get the last colin event id for the identifier."""
    query = db.session.execute(
        f"""
        select max(colin_event_id) from colin_event_ids
            join filings on filings.id = colin_event_ids.filing_id
            join businesses on businesses.id = filings.business_id
        where businesses.identifier = '{identifier}'
        limit 1
        """
    )
    last_event_id = query.scalar()
    if not last_event_id:
        return {'message': 'No colin ids found'}, HTTPStatus.NOT_FOUND

    return {'maxId': last_event_id}, HTTPStatus.OK


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
