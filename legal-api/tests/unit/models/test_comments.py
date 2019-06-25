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

"""Tests to assure the Comment Model.

Test-Suite to ensure that the Comment Model is working as expected.
"""
import datetime
from http import HTTPStatus

import pytest

from legal_api.exceptions import BusinessException
from legal_api.models import Business, Comment
from tests import EPOCH_DATETIME, FROZEN_DATETIME


def factory_business(session, identifier):
    """Create a business entity."""
    business = Business(legal_name=f'legal_name-{identifier}',
                        founding_date=EPOCH_DATETIME,
                        dissolution_date=EPOCH_DATETIME,
                        identifier=identifier,
                        tax_id='BN123456789',
                        fiscal_year_end_date=FROZEN_DATETIME)
    business.save()
    return business


# def test_minimal_filing_json(session):
#     """Assert that a minimal filing can be created."""
#     b = factory_business('CP1234567')

#     data = {'filing': 'not a real filing, fail validation'}

#     filing = Filing()
#     filing.business_id = b.id
#     filing.filing_date = datetime.datetime.utcnow()
#     filing.filing_data = json.dumps(data)
#     filing.save()

#     assert filing.id is not None


def test_comment_block_orm_delete(session):
    """Assert that attempting to delete a filing will raise a BusinessException."""
    from legal_api.exceptions import BusinessException

    b = factory_business(session, 'CP1234567')
    c = Comment()
    c.business_id = b.id
    c.timestamp = EPOCH_DATETIME
    c.comment = 'a comment'
    c.save()

    with pytest.raises(BusinessException) as excinfo:
        session.delete(c)
        session.commit()

    assert excinfo.value.status_code == HTTPStatus.FORBIDDEN
    assert excinfo.value.error == 'Deletion not allowed.'


def test_comment_delete_is_blocked(session):
    """Assert that an AR filing can be saved."""
    c = Comment()

    with pytest.raises(BusinessException) as excinfo:
        c.delete()

    assert excinfo.value.status_code == HTTPStatus.FORBIDDEN
    assert excinfo.value.error == 'Deletion not allowed.'


def test_comment_dump_json(session):
    """Assert the comment json serialization works correctly."""
    identifier = 'CP7654321'
    b = factory_business(session, identifier)
    c = Comment()
    c.business_id = b.id
    c.timestamp = EPOCH_DATETIME
    c.comment = 'a comment'

    assert c.json() == {'comment': 'a comment',
                        'id': None,
                        'staff': 'unknown',
                        'timestamp': datetime.datetime(1970, 1, 1, 0, 0)}


def test_comment_save_to_session(session):
    """Assert the comment is saved toThe session, but not committed."""
    from sqlalchemy.orm.session import Session
    # b = factory_business('CP1234567')
    # filing = factory_filing(b, AR_FILING)

    comment = Comment()

    assert not session.new
    assert not Session.object_session(comment)

    comment.save_to_session()

    assert comment.id is None
    assert session.new
    assert Session.object_session(comment)


def test_comment_save(session):
    """Assert that the comment was saved."""
    from sqlalchemy.orm.session import Session
    b = factory_business(session, 'CP1234567')

    comment = Comment()
    comment.business_id = b.id
    comment.timestamp = EPOCH_DATETIME
    comment.comment = 'a comment'

    assert not session.new
    assert not Session.object_session(comment)

    comment.save()

    assert comment.id
    assert not session.dirty
    assert Session.object_session(comment)
