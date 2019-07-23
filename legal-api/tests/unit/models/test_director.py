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

"""Tests to assure the Director Model.

Test-Suite to ensure that the Director Model is working as expected.
"""
import datetime

from legal_api.models import Director
from tests.unit.models import factory_business


def test_director_json(session):
    """Assert the json format of director."""
    director = Director(
        first_name='Michael',
        last_name='Crane',
        middle_initial='Joe',
        title='VP',
        appointment_date=datetime.datetime(2017, 5, 17),
        cessation_date=None
    )

    director_json = {
        'appointmentDate': director.appointment_date.date().isoformat(),
        'cessationDate': director.cessation_date,
        'officer': {
            'firstName': director.first_name,
            'lastName': director.last_name,
            'middleInitial': director.middle_initial
        },
        'title': director.title
    }

    assert director.json == director_json


def test_director_save(session):
    """Assert that the director saves correctly."""
    director = Director(
        first_name='Michael',
        last_name='Crane',
        middle_initial='Joe',
        title='VP',
        appointment_date=datetime.datetime(2017, 5, 17),
        cessation_date=None
    )

    director.save()
    assert director.id


def test_director_save_to_business(session):
    """Assert that the director saves correctly."""
    identifier = 'CP1234567'
    business = factory_business(identifier)

    director1 = Director(
        first_name='Michael',
        last_name='Crane',
        middle_initial='Joe',
        title='VP',
        appointment_date=datetime.datetime(2020, 5, 17),
        cessation_date=None
    )

    director2 = Director(
        first_name='Scott',
        last_name='James',
        middle_initial=None,
        title='AVP',
        appointment_date=datetime.datetime(2017, 5, 17),
        cessation_date=None
    )

    business.directors.append(director1)
    business.directors.append(director2)
    business.save()

    directors = business.directors.all()
    assert len(directors) == 2
