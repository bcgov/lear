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
"""Finds all the cases where directors with the same name exist across two
or more companies and creates a new entry of that director in the parties table for each company.
"""
from dotenv import load_dotenv, find_dotenv

from flask import Flask
from legal_api import db
from legal_api.config import get_named_config
from legal_api.models import Party, PartyRole

import copy

load_dotenv(find_dotenv())

FLASK_APP = Flask(__name__)
FLASK_APP.config.from_object(get_named_config('production'))
db.init_app(FLASK_APP)

def copy_over_dirs():
    # add directors as party members
    select_string1 = 'select id, party_id, business_id from party_roles where party_id in (select party_id from (select count(*) as b, party_id from party_roles where cessation_date is null group by (party_id)) as a where b > 1 order by b desc) order by party_id'
    party_roles = db.session.execute(select_string1)
    count = 0
    parties = []
    for row in party_roles:
        print(row[0])
        if row[1] in parties:
            select_string2 = f'select delivery_address_id from parties where id={row[1]}'
            deliv_id = db.session.execute(select_string2)
            for d in deliv_id:
                print(d)
                select_string3 = f'insert into addresses (address_type, street, city, region, country, postal_code) select address_type, street, city, region, country, postal_code from addresses where id={d[0]} returning id'
                insert_addr = db.session.execute(select_string3)
                for addr_id in insert_addr:
                    print(addr_id)
                    select_string4 = f'insert into parties (party_type, first_name, middle_initial, last_name, delivery_address_id) select party_type, first_name, middle_initial, last_name, delivery_address_id from parties where id={row[1]} returning id'
                    insert_party = db.session.execute(select_string4)
                    for party_id in insert_party:
                        print(party_id)
                        db.session.execute(f'update parties set delivery_address_id={addr_id[0]} where id={party_id[0]}')
                        db.session.execute(f'update party_roles set party_id={party_id[0]} where id={row[0]}')
                        db.session.commit()
        else:
            parties.append(row[1])

with FLASK_APP.app_context():
    copy_over_dirs()