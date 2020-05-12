"""Endpoints for importing, exporting, and clearing business data."""
import io
from http import HTTPStatus
from zipfile import ZipFile

import pandas
import psycopg2
from flask import Blueprint, current_app, jsonify, request, send_file


FIXTURE_BLUEPRINT = Blueprint('fixture', __name__)


@FIXTURE_BLUEPRINT.route('/api/fixture/import', methods=['POST'], strict_slashes=False)
@FIXTURE_BLUEPRINT.route('/api/fixture/import/<table>', methods=['POST'], strict_slashes=False)
def post(table=None):
    """Import csv data into given table."""
    if not request.files.keys():
        return jsonify({'message': f'No csv files given for import.'}), HTTPStatus.BAD_REQUEST
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

        csv_list = [f'{table}'] if table \
            else ['businesses', 'filings', 'offices', 'addresses', 'parties-addresses', 'parties', 'party_roles']

        for filename in csv_list:
            table = 'addresses' if filename == 'parties-addresses' else filename
            input_file = request.files[f'{filename}']
            try:
                # delete existing entries
                csv_data = pandas.read_csv(input_file)
                ids = str(csv_data.id.to_list())
                ids = ids.replace('[', '(').replace(']', ')')
                if table == 'addresses':
                    cur.execute(f'update parties set delivery_address_id=null where delivery_address_id in {ids}')

                cur.execute(f'delete from {table} where id in {ids}')
                if 'DELETE' not in cur.statusmessage:
                    current_app.logger.error('Delete command did not run.')
                    raise Exception

            except Exception as err:
                current_app.logger.error(f'Failed to delete existing entries: {err}')

            # set reader back to beginning of file and import csv into table
            input_file.seek(0)
            cur.copy_expert(f"COPY {table} from stdin delimiter ',' csv header", input_file)

        con.commit()
        return jsonify({'message': 'Success!'}), HTTPStatus.CREATED

    except Exception as err:
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
            all_tables = ['businesses', 'filings', 'offices', 'party_roles', 'parties', 'addresses']
            for item in all_tables:
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

    except Exception as err:
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

        party_ids = _get_id_list(
            cur=cur, column='party_id', table='party_roles', table_val='business_id', val=business_id
        )
        office_ids = _get_id_list(cur=cur, column='id', table='offices', table_val='business_id', val=business_id)
        filing_ids = _get_id_list(cur=cur, column='id', table='filings', table_val='business_id', val=business_id)

        # delete all data for given business
        cur.execute(
            f"""
            delete from party_roles where business_id={business_id};
            delete from parties where id in {party_ids};
            delete from addresses where office_id in {office_ids};
            delete from offices where business_id={business_id};
            delete from colin_event_ids where filing_id in {filing_ids};
            delete from filings where id in {filing_ids};
            delete from businesses where id={business_id};
            """
        )
        con.commit()
        return jsonify(
            {'message': f'Successfully deleted all data for {business_identifier}'}
        ), HTTPStatus.OK

    except Exception as err:
        current_app.logger.error(f'Failed when trying to delete: {err}')
        con.rollback()
        return jsonify({'message': f'Failed to delete {business_identifier}.'}), HTTPStatus.INTERNAL_SERVER_ERROR


def _get_business_id(cur: psycopg2.extensions.cursor, business_identifier: str):
    """Return the business id for the given identifier."""
    cur.execute(f"select id from businesses where identifier='{business_identifier}'")
    business_id = cur.fetchone()
    if not business_id:
        return ''
    return str(business_id[0])


def _get_id_list(cur: psycopg2.extensions.cursor, column: str, table: str, table_val: str, val: str):
    """Return a stringified list of ids for the given table linked to the business_id."""
    val = val.replace('(', '').replace(')', '')
    cur.execute(f'select {column} from {table} where {table_val} in ({val})')
    id_list = []
    for _id in cur.fetchall():
        id_list.append(_id[0])
    return str(id_list).replace('[', '(').replace(']', ')')


def _create_csv(cur: psycopg2.extensions.cursor, filename: str, select_stmnt: str):
    """Create or update given csv file with db data for given select statement."""
    with open(f'exports/{filename}.csv', 'wb') as csvfile:
        cur.copy_expert(f'COPY ({select_stmnt}) to stdout with csv header', csvfile)
    return f'{filename}.csv'


def _copy_from_table(cur: psycopg2.extensions.cursor, table: str, business_id: str):
    """Copy db data into csv files for given table."""
    files = []
    select_stmnt = ''
    if table in ['filings', 'offices', 'party_roles']:
        # copy from table based on business_id
        id_list = _get_id_list(cur=cur, column='id', table=table, table_val='business_id', val=business_id)
        select_stmnt = f'select * from {table} where id in {id_list}'

    elif table == 'parties':
        # copy parties and their addresses based on party_id and delivery_address_id
        # get party ids from party roles table
        id_list = _get_id_list(
            cur=cur, column='party_id', table='party_roles', table_val='business_id', val=business_id
        )
        # get address ids from parties table
        addr_id_list = _get_id_list(
            cur=cur, column='delivery_address_id', table='parties', table_val='id', val=id_list
        )
        # create address csv for party addresses
        addresses_stmnt = f'select * from addresses where id in {addr_id_list}'
        files.append(_create_csv(cur=cur, filename=f'{table}-addresses', select_stmnt=addresses_stmnt))

        select_stmnt = f'select * from {table} where id in {id_list}'

    elif table == 'addresses':
        # copy from addresses based on offices ids
        id_list = _get_id_list(cur=cur, column='id', table='offices', table_val='business_id', val=business_id)
        select_stmnt = f'select * from {table} where office_id in {id_list}'

    elif table == 'businesses':
        # copy from businesses table
        select_stmnt = f'select * from {table} where id={business_id}'
    else:
        current_app.logger.error(f'No export built for {table}.')
        return []

    files.append(_create_csv(cur=cur, filename=table, select_stmnt=select_stmnt))
    return files
