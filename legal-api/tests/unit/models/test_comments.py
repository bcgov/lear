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
from freezegun import freeze_time
from registry_schemas.example_data import ANNUAL_REPORT

from legal_api.exceptions import BusinessException
from legal_api.models import Comment
from tests import EPOCH_DATETIME
from tests.unit.models import factory_business, factory_comment, factory_filing


def test_minimal_comment(session):
    """Assert that a minimal comment can be created."""
    comment = Comment()
    comment.comment = 'some words'
    comment.save()

    assert comment.id is not None


def test_comment_block_orm_delete(session):
    """Assert that attempting to delete a filing will raise a BusinessException."""
    from legal_api.exceptions import BusinessException

    c = factory_comment()

    with pytest.raises(BusinessException) as excinfo:
        session.delete(c)
        session.commit()

    assert excinfo.value.status_code == HTTPStatus.FORBIDDEN
    assert excinfo.value.error == 'Deletion not allowed.'


def test_comment_delete_is_blocked(session):
    """Assert that an AR filing can be saved."""
    c = factory_comment()

    with pytest.raises(BusinessException) as excinfo:
        c.delete()

    assert excinfo.value.status_code == HTTPStatus.FORBIDDEN
    assert excinfo.value.error == 'Deletion not allowed.'


def test_filing_comment_dump_json(session):
    """Assert the comment json serialization works correctly."""
    identifier = 'CP7654321'
    b = factory_business(identifier)
    f = factory_filing(b, ANNUAL_REPORT)
    c = factory_comment(b, f, 'a comment')

    now = datetime.datetime(1970, 1, 1, 0, 0).replace(tzinfo=datetime.timezone.utc)
    with freeze_time(now):
        assert c.json == {
            'comment': {
                'id': c.id,
                'submitterDisplayName': 'Registry Staff',
                'comment': 'a comment',
                'filingId': f.id,
                'businessId': None,
                'timestamp': now.isoformat()
            }
        }


def test_comment_save_to_session(session):
    """Assert that the comment is saved to the session but not committed."""
    from sqlalchemy.orm.session import Session

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

    comment = Comment()
    comment.timestamp = EPOCH_DATETIME
    comment.comment = 'a comment'

    assert not session.new
    assert not Session.object_session(comment)

    comment.save()

    assert comment.id
    assert not session.dirty
    assert Session.object_session(comment)
