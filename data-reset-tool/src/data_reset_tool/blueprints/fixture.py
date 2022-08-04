"""Endpoints for importing, exporting, and clearing business data."""
import copy
import io
from http import HTTPStatus
from zipfile import ZipFile

import pandas
import psycopg2
from flask import Blueprint, current_app, jsonify, request, send_file
from legal_api.models import Business


FIXTURE_BLUEPRINT = Blueprint('fixture', __name__)

ALL_BCOMP_TABLES = \
    [
        'aliases_version',
        'aliases',
        'resolutions_version',
        'resolutions',
        'share_series_version',
        'share_series',
        'share_classes_version',
        'share_classes',
        'party_roles_version',
        'party_roles',
        'parties_version',
        'parties',
        'parties_version-addresses_version',
        'parties_version-addresses',
        'parties-addresses_version',
        'parties-addresses',
        'addresses_version',
        'addresses',
        'offices_version',
        'offices',
        'filings',
        'businesses_version',
        'businesses',
        'transaction'
    ]

ALL_COOP_TABLES = \
    [
        'party_roles_version',
        'party_roles',
        'parties-addresses_version',
        'parties-addresses',
        'parties_version',
        'parties',
        'addresses_version',
        'addresses',
        'offices_version',
        'offices',
        'filings',
        'businesses_version',
        'businesses',
        'transaction'
    ]


@FIXTURE_BLUEPRINT.route('/api/fixture/import/<legal_type>', methods=['POST'], strict_slashes=False)
@FIXTURE_BLUEPRINT.route('/api/fixture/import/<legal_type>/<table>', methods=['POST'], strict_slashes=False)
def post(legal_type, table=None):
    """Import csv data into given table."""
    if not request.files.keys():
        return jsonify({'message': 'No csv files given for import.'}), HTTPStatus.BAD_REQUEST
    # data to import
    try:
        # connection to db
        con = current_app.config.get('DB_CONNECTION', None)
        if not con:
            current_app.logger.error('Database connection failure.')
            return jsonify(
                {'message': 'Database connection error, this service is down :('}
            ), HTTPStatus.INTERNAL_SERVER_ERROR
        cur = con.cursor()

        if table:
            csv_list = [f'{table}']
        elif legal_type == Business.LegalTypes.BCOMP.value:
            csv_list = copy.deepcopy(ALL_BCOMP_TABLES)
        else:
            csv_list = copy.deepcopy(ALL_COOP_TABLES)
        csv_list.reverse()
        for filename in csv_list:
            table = filename.replace('parties_version-', '').replace('parties-', '')
            input_file = request.files.get(f'{filename}')
            if input_file:
                try:
                    # delete existing entries
                    csv_data = pandas.read_csv(input_file)
                    ids = str(csv_data.id.to_list())
                    ids = ids.replace('[', '(').replace(']', ')')
                    if table in ['addresses', 'addresses_version']:
                        cur.execute(
                            f'update parties set delivery_address_id=null, mailing_address_id=null \
                                where delivery_address_id in {ids} or mailing_address_id in {ids}'
                        )
                        cur.execute(
                            f'update parties_version set delivery_address_id=null, mailing_address_id=null \
                                where delivery_address_id in {ids} or mailing_address_id in {ids}'
                        )

                    cur.execute(f'delete from {table} where id in {ids}')
                    if 'DELETE' not in cur.statusmessage:
                        current_app.logger.error('Delete command did not run.')
                        raise Exception

                except Exception as err:  # noqa: B902
                    current_app.logger.error(f'Failed to delete existing entries: {err}')

                # set reader back to beginning of file and import csv into table
                input_file.seek(0)
                cur.copy_expert(f"COPY {table} from stdin delimiter ',' csv header", input_file)

        con.commit()
        return jsonify({'message': 'Success!'}), HTTPStatus.CREATED

    except Exception as err:  # noqa: B902
        current_app.logger.error(f'Failed to import: {err}')
        con.rollback()
        return jsonify({'message': 'Failed to import data.'}), HTTPStatus.INTERNAL_SERVER_ERROR


@FIXTURE_BLUEPRINT.route('/api/fixture/export/<business_identifier>', methods=['GET'], strict_slashes=False)
@FIXTURE_BLUEPRINT.route('/api/fixture/export/<business_identifier>/<table>', methods=['GET'], strict_slashes=False)
def get(business_identifier, table=None):
    """Get business data for either all tables or a specified table. Output as csv per table."""
    con = current_app.config.get('DB_CONNECTION', None)
    if not con:
        current_app.logger.error('Database connection failure.')
        return jsonify(
            {'message': 'Database connection error, this service is down :('}
        ), HTTPStatus.INTERNAL_SERVER_ERROR
    cur = con.cursor()

    business_id = _get_business_id(cur=cur, business_identifier=business_identifier)
    if not business_id:
        current_app.logger.error(f'{business_identifier} not found.')
        return jsonify({'message': f'Could not find {business_identifier}.'}), HTTPStatus.NOT_FOUND

    try:
        export_name = business_identifier
        csv_files = []
        if table:
            export_name = f'{business_identifier}-{table}'
            csv_files = _copy_from_table(cur=cur, table=table, business_id=business_id)
        else:
            for item in ALL_BCOMP_TABLES:
                csv_files += _copy_from_table(cur=cur, table=item, business_id=business_id)
        if not csv_files:
            return jsonify(
                {'message': f'Failed to create csvs for {business_identifier}'}
            ), HTTPStatus.INTERNAL_SERVER_ERROR

        data = io.BytesIO()
        with ZipFile(data, 'w') as zip_obj:
            # Add multiple files to the zip
            for filename in csv_files:
                zip_obj.write(f'exports/{filename}')
        data.seek(0)
        return send_file(
            data, attachment_filename=f'{export_name}.zip', as_attachment=True, mimetype='application/zip'
        ), HTTPStatus.OK

    except Exception as err:  # noqa: B902
        current_app.logger.error(f'Failed to export: {err}')
        con.reset()
        return jsonify({'message': 'Failed to export data.'}), HTTPStatus.INTERNAL_SERVER_ERROR


@FIXTURE_BLUEPRINT.route('/api/fixture/delete/<business_identifier>', methods=['DELETE'], strict_slashes=False)
def delete(business_identifier):
    """Delete complete business data."""
    # connection to db
    con = current_app.config.get('DB_CONNECTION', None)
    if not con:
        current_app.logger.error('Database connection failure.')
        return jsonify(
            {'message': 'Database connection error, this service is down :('}
        ), HTTPStatus.INTERNAL_SERVER_ERROR
    cur = con.cursor()
    try:
        # get ids for deletion across all tables
        business_id = _get_business_id(cur=cur, business_identifier=business_identifier)
        if not business_id:
            current_app.logger.error(f'{business_identifier} not found.')
            return jsonify({'message': f'Could not find {business_identifier}.'}), HTTPStatus.NOT_FOUND

        share_class_ids = _get_id_list(
            cur=cur, column='id', table='share_classes', table_val='business_id', val=business_id)
        share_class_version_ids = _get_id_list(
            cur=cur, column='id', table='share_classes_version', table_val='business_id', val=business_id)
        party_ids = _get_id_list(
            cur=cur, column='party_id', table='party_roles', table_val='business_id', val=business_id)
        office_ids = _get_id_list(cur=cur, column='id', table='offices', table_val='business_id', val=business_id)
        filing_ids = _get_id_list(cur=cur, column='id', table='filings', table_val='business_id', val=business_id)
        transaction_ids = _get_id_list(
            cur=cur, column='transaction_id', table='filings', table_val='business_id', val=business_id)
        # delete all data for given business
        cur.execute(
            f"""
            delete from party_roles_version where business_id={business_id};
            delete from party_roles where business_id={business_id};
            """
        )
        if _share_series_exists(cur, 'share_series_version', share_class_ids):
            cur.execute(
                f"""
                delete from share_series_version where share_class_id in {share_class_ids};
                """
            )
        if _share_series_exists(cur, 'share_series_version', share_class_version_ids):
            cur.execute(
                f"""
                delete from share_series_version where share_class_id in {share_class_ids};
                """
            )
        if _share_series_exists(cur, 'share_series', share_class_ids):
            cur.execute(
                f"""
                delete from share_series where id in {share_class_ids};
                """
            )
        if party_ids:
            cur.execute(
                f"""
                delete from parties_version where id in {party_ids};
                delete from parties where id in {party_ids};
                """
            )
        if office_ids:
            cur.execute(
                f"""
                delete from addresses_version where office_id in {office_ids};
                delete from addresses where office_id in {office_ids};
                """
            )
        if filing_ids:
            cur.execute(
                f"""
                delete from colin_event_ids where filing_id in {filing_ids};
                """
            )
        if transaction_ids:
            cur.execute(
                f"""
                delete from filings where business_id={business_id};
                delete from transaction where id in {transaction_ids};
                """
            )
        cur.execute(
            f"""
            delete from aliases_version where business_id={business_id};
            delete from aliases where business_id={business_id};
            delete from resolutions_version where business_id={business_id};
            delete from resolutions where business_id={business_id};
            delete from share_classes_version where business_id={business_id};
            delete from share_classes where business_id={business_id};
            delete from offices_version where business_id={business_id};
            delete from offices where business_id={business_id};
            delete from businesses_version where id={business_id};
            delete from businesses where id={business_id};
            """
        )
        con.commit()
        return jsonify(
            {'message': f'Successfully deleted all data for {business_identifier}'}
        ), HTTPStatus.OK

    except Exception as err:  # noqa: B902
        current_app.logger.error(f'Failed when trying to delete: {err}')
        con.rollback()
        return jsonify({'message': f'Failed to delete {business_identifier}.'}), HTTPStatus.INTERNAL_SERVER_ERROR


def _get_business_id(cur: psycopg2.extensions.cursor, business_identifier: str) -> str:
    """Return the business id for the given identifier."""
    cur.execute(f"select id from businesses where identifier='{business_identifier}'")
    business_id = cur.fetchone()
    if not business_id:
        return ''
    return str(business_id[0])


def _get_id_list(cur: psycopg2.extensions.cursor, column: str, table: str, table_val: str, val: str) -> str:
    """Return a stringified list of ids for the given table linked to the business_id."""
    val = val.replace('(', '').replace(')', '')
    if not val:
        return ''
    cur.execute(f'select {column} from {table} where {table_val} in ({val})')
    id_list = []
    for _id in cur.fetchall():
        if _id[0]:
            id_list.append(_id[0])
    if not id_list:
        return ''
    return str(id_list).replace('[', '(').replace(']', ')')


def _create_csv(cur: psycopg2.extensions.cursor, filename: str, select_stmnt: str) -> str:
    """Create or update given csv file with db data for given select statement."""
    with open(f'exports/{filename}.csv', 'wb') as csvfile:
        cur.copy_expert(f'COPY ({select_stmnt}) to stdout with csv header', csvfile)
    return f'{filename}.csv'


def _copy_from_table(cur: psycopg2.extensions.cursor, table: str, business_id: str) -> list:
    # pylint: disable=too-many-branches
    """Copy db data into csv files for given table."""
    files = []
    select_stmnt = ''

    if table in [
        'aliases_version',
        'aliases',
        'resolutions_version',
        'resolutions',
        'share_classes_version',
        'share_classes',
        'party_roles_version',
        'party_roles',
        'offices_version',
        'offices',
        'filings'
    ]:
        # copy from table based on business_id
        id_list = _get_id_list(cur=cur, column='id', table=table, table_val='business_id', val=business_id)
        if id_list:
            select_stmnt = f'select * from {table} where id in {id_list}'

    elif table in ['parties', 'parties_version']:
        # copy parties and their addresses based on party_id and delivery_address_id
        # get party ids from party roles table
        id_list = _get_id_list(
            cur=cur, column='party_id', table='party_roles', table_val='business_id', val=business_id
        )
        if id_list:
            # get address ids from parties table
            addr_id_list = ''
            deliv_addr_id_list = _get_id_list(
                cur=cur, column='delivery_address_id', table='parties', table_val='id', val=id_list)
            addr_id_list = str(deliv_addr_id_list).replace('(', '').replace(')', '')
            addr_id_list = addr_id_list + ',' if addr_id_list else addr_id_list

            mail_addr_id_list = _get_id_list(
                cur=cur, column='mailing_address_id', table='parties', table_val='id', val=id_list)
            addr_id_list += str(mail_addr_id_list).replace('(', '').replace(')', '')

            # create address csv for party mailing addresses
            if addr_id_list:
                addr_id_list = '(' + addr_id_list + ')'
                addresses_stmnt = f'select * from addresses where id in {addr_id_list}'
                addresses_version_stmnt = f'select * from addresses_version where id in {addr_id_list}'
                files.append(_create_csv(cur=cur, filename=f'{table}-addresses', select_stmnt=addresses_stmnt))
                files.append(
                    _create_csv(cur=cur, filename=f'{table}-addresses_version', select_stmnt=addresses_version_stmnt))
            select_stmnt = f'select * from {table} where id in {id_list}'

    elif table in ['addresses', 'addresses_version']:
        # copy from addresses based on offices ids
        id_list = _get_id_list(cur=cur, column='id', table='offices', table_val='business_id', val=business_id)
        if id_list:
            select_stmnt = f'select * from {table} where office_id in {id_list}'

    elif table in ['share_series', 'share_series_version']:
        # copy from share series based on share classes ids
        share_class_version_ids = _get_id_list(
            cur=cur, column='id', table='share_classes_version', table_val='business_id', val=business_id)
        share_class_ids = _get_id_list(
            cur=cur, column='id', table='share_classes', table_val='business_id', val=business_id)
        # only create this select statement if there is a valid share series
        if table == 'share_series_version':
            if _share_series_exists(cur, table, share_class_ids) or _share_series_exists(
                cur, table, share_class_version_ids
            ):
                select_stmnt = f'select * from {table} where share_class_id in {share_class_ids}'
        elif _share_series_exists(cur, table, share_class_ids):
            select_stmnt = f'select * from {table} where share_class_id in {share_class_ids}'

    elif table in ['transaction']:
        # copy from transactions based on filing transaction ids
        id_list = _get_id_list(
            cur=cur, column='transaction_id', table='filings', table_val='business_id', val=business_id)
        if id_list:
            select_stmnt = f'select * from {table} where id in {id_list}'

    elif table in ['businesses', 'businesses_version']:
        # copy from businesses table
        select_stmnt = f'select * from {table} where id={business_id}'

    else:
        # otherwise handled elsewhere
        if table not in [
            'parties-addresses_version',
            'parties-addresses',
            'parties_version-addresses_version',
            'parties_version-addresses'
        ]:
            current_app.logger.error(f'No export built for {table}.')

    if select_stmnt:
        files.append(_create_csv(cur=cur, filename=table, select_stmnt=select_stmnt))

    return files


def _share_series_exists(cur: psycopg2.extensions.cursor, table: str, share_class_ids: list) -> bool:
    share_series = None
    for share_class_id in share_class_ids:
        share_series = _get_id_list(
            cur=cur, column='id', table=f'{table}', table_val='share_class_id', val=share_class_id)
        if share_series:
            break

    return share_series is not None
