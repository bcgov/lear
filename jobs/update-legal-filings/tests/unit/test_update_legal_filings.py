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

"""Tests to assure the business end-point.

Test-Suite to ensure that the /businesses endpoint is working as expected.
"""
import config
import psycopg2
import update_legal_filings


def prep_database(pg_conn):
    # insert event id = 111362554
    # insert CP0001965
    cursor = pg_conn.cursor()

    cursor.execute(
        """
        delete from colin_last_update;
        delete from filings;
        delete from businesses;
        insert into colin_last_update (last_event_id, last_update) 
        values (111362554, '2018-01-01');
        insert into businesses (last_modified, identifier, legal_name, founding_date)
        values ('2018-01-01', 'CP0001965', 'CENTRAL INTERIOR COMMUNITY SERVICES CO-OP', '2018-01-01');
        """
    )
    pg_conn.commit()


def setup_db_conn():
    pg_conn = psycopg2.connect(
        host=config.ProdConfig.DB_HOST,
        user=config.ProdConfig.DB_USER,
        password=config.ProdConfig.DB_PASSWORD,
        dbname=config.ProdConfig.DB_NAME
    )
    return pg_conn


def test_update_legal(client):
    # run main from update_legal_filings
    # check legal db for ar filing was made
    pg_conn = setup_db_conn()
    prep_database(pg_conn=pg_conn)
    update_legal_filings.run()
    cursor = pg_conn.cursor()
    cursor.execute(
        """
        select * from filings
        """
    )
    filing = cursor.fetchone()
    filing = dict(zip([x[0].lower() for x in cursor.description], filing))
    assert filing['colin_event_id'] == 111362555

    cursor.execute(
        """
        select * from colin_last_update
        """
    )

    passed = False
    last_update_info = cursor.fetchall()
    for info in last_update_info:
        info = dict(zip([x[0].lower() for x in cursor.description], info))
        if info['last_event_id'] == 111362555:
            passed = True
            break

    assert passed
    pg_conn.close()


def test_update_legal_skips_dups():
    # test that job doesn't send filings already in legal
    pg_conn = setup_db_conn()
    cursor = pg_conn.cursor()
    cursor.execute(
        """
        delete from colin_last_update where last_event_id=111362555;
        select id from filings;
        """
    )
    original = cursor.fetchall()
    update_legal_filings.run()
    cursor.execute(
        """
        select id from filings;
        """
    )
    present = cursor.fetchall()

    assert original == present
    pg_conn.close()


def test_update_legal_no_updates():
    # test that job doesn't run when last_event_id in legaldb == highest event_id in colindb
    pg_conn = setup_db_conn()
    prep_database(pg_conn=pg_conn)
    cursor = pg_conn.cursor()
    cursor.execute(
        """
        insert into colin_last_update (last_event_id, last_update) 
        values (111362555, '2018-01-01');    
        """
    )
    pg_conn.commit()
    update_legal_filings.run()
    cursor.execute(
        """
        select * from filings
        """
    )
    assert not cursor.fetchone()
    pg_conn.close()
