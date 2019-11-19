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
""" Associates offices with entities (COOPs) loaded before creation of the offices table."""
from dotenv import load_dotenv, find_dotenv

from flask import Flask
from legal_api import db
from legal_api.config import get_named_config
from legal_api.models import Business, Office


load_dotenv(find_dotenv())

FLASK_APP = Flask(__name__)
FLASK_APP.config.from_object(get_named_config('production'))
db.init_app(FLASK_APP)


def add_business_office_records():
    """Iterate all business entries and associate a records office if needed."""

    businesses = db.session.query(Business).all() #pylint: disable=no-member; needed by SQLAlchemy

    for business in businesses:
        if not any(business.offices):
            office = Office()
            office.office_type = 'registeredOffice'
            office.addresses = [business.mailing_address.one_or_none(),
                                business.delivery_address.one_or_none()]
            db.session.add(office) #pylint: disable=no-member; needed by SQLAlchemy
            db.session.add(business) #pylint: disable=no-member; needed by SQLAlchemy
            db.session.commit() #pylint: disable=no-member; needed by SQLAlchemy

with FLASK_APP.app_context():
    add_business_office_records()
