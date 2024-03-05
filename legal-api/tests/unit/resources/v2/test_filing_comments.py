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

"""Tests to assure the filing-comment endpoint.

Test-Suite to ensure that the filings/<filing_id>/comments endpoint is working as expected.
"""
import copy
from http import HTTPStatus

from freezegun import freeze_time
from registry_schemas.example_data import ANNUAL_REPORT, COMMENT_FILING

from legal_api.models import User
from legal_api.services.authz import BASIC_USER, STAFF_ROLE
from legal_api.utils import datetime
from tests.unit import nested_session
from tests.unit.models import factory_comment, factory_filing, factory_legal_entity
from tests.unit.services.utils import create_header

# prep sample post data for single comment
SAMPLE_JSON_DATA = copy.deepcopy(COMMENT_FILING)
del SAMPLE_JSON_DATA["comment"]["timestamp"]
del SAMPLE_JSON_DATA["comment"]["submitterDisplayName"]


def test_get_all_filing_comments_no_results(session, client, jwt):
    """Assert that endpoint returns no-results correctly."""
    with nested_session(session):
        identifier = "CP7654321"
        b = factory_legal_entity(identifier)
        f = factory_filing(b, ANNUAL_REPORT)

        rv = client.get(
            f"/api/v2/businesses/{identifier}/filings/{f.id}/comments", headers=create_header(jwt, [STAFF_ROLE])
        )

        assert rv.status_code == HTTPStatus.OK
        assert 0 == len(rv.json.get("comments"))


def test_get_all_filing_comments_only_one(session, client, jwt):
    """Assert that a list of comments with a single comment is returned correctly."""
    with nested_session(session):
        identifier = "CP7654321"
        b = factory_legal_entity(identifier)
        f = factory_filing(b, ANNUAL_REPORT)
        factory_comment(b, f)

        rv = client.get(
            f"/api/v2/businesses/{identifier}/filings/{f.id}/comments", headers=create_header(jwt, [STAFF_ROLE])
        )

        assert HTTPStatus.OK == rv.status_code
        assert 1 == len(rv.json.get("comments"))


def test_get_all_business_filings_multiple(session, client, jwt):
    """Assert that multiple filings are returned correctly."""
    with nested_session(session):
        identifier = "CP7654321"
        b = factory_legal_entity(identifier)
        f = factory_filing(b, ANNUAL_REPORT)
        factory_comment(b, f)
        factory_comment(b, f, "other text")

        rv = client.get(
            f"/api/v2/businesses/{identifier}/filings/{f.id}/comments", headers=create_header(jwt, [STAFF_ROLE])
        )

        assert HTTPStatus.OK == rv.status_code
        assert 2 == len(rv.json.get("comments"))


def test_get_one_filing_comment_by_id(session, client, jwt):
    """Assert that a single comment is returned correctly."""
    with nested_session(session):
        identifier = "CP7654321"
        b = factory_legal_entity(identifier)
        f = factory_filing(b, ANNUAL_REPORT)
        c = factory_comment(b, f, "some specific text")

        rv = client.get(
            f"/api/v2/businesses/{identifier}/filings/{f.id}/comments/{c.id}", headers=create_header(jwt, [STAFF_ROLE])
        )

        assert HTTPStatus.OK == rv.status_code
        assert "some specific text" == rv.json.get("comment").get("comment")


def test_comment_json_output(session, client, jwt):
    """Assert the json output of a comment is correctly formatted."""
    with nested_session(session):
        identifier = "CP7654321"
        b = factory_legal_entity(identifier)
        f = factory_filing(b, ANNUAL_REPORT)
        u = User(
            username="username",
            firstname="firstname",
            lastname="lastname",
            sub="sub",
            iss="iss",
            idp_userid="123",
            login_source="IDIR",
        )
        u.save()

        now = datetime.datetime(1970, 1, 1, 0, 0).replace(tzinfo=datetime.timezone.utc)
        with freeze_time(now):
            c = factory_comment(b, f, "some specific text", u)

            rv = client.get(
                f"/api/v2/businesses/{identifier}/filings/{f.id}/comments/{c.id}",
                headers=create_header(jwt, [STAFF_ROLE]),
            )

            assert HTTPStatus.OK == rv.status_code
            assert "some specific text" == rv.json.get("comment").get("comment")
            assert "firstname lastname" == rv.json.get("comment").get("submitterDisplayName")
            assert now.isoformat() == rv.json.get("comment").get("timestamp")


def test_get_comments_mismatch_business_filing_error(session, client, jwt):
    """Assert that error is returned when filing isn't owned by business."""
    with nested_session(session):
        b1 = factory_legal_entity("CP1111111")
        b2 = factory_legal_entity("CP2222222")
        f = factory_filing(b2, ANNUAL_REPORT)

        rv = client.get(
            f"/api/v2/businesses/{b1.identifier}/filings/{f.id}/comments", headers=create_header(jwt, [STAFF_ROLE])
        )

        assert HTTPStatus.NOT_FOUND == rv.status_code
        assert f"Filing {f.id} not found" == rv.json.get("message")


def test_get_comments_invalid_business_error(session, client, jwt):
    """Assert that error is returned when business doesn't exist."""
    with nested_session(session):
        b = factory_legal_entity("CP1111111")
        f = factory_filing(b, ANNUAL_REPORT)

        rv = client.get(
            f"/api/v2/businesses/CP2222222/filings/{f.id}/comments", headers=create_header(jwt, [STAFF_ROLE])
        )

        assert HTTPStatus.NOT_FOUND == rv.status_code
        assert "CP2222222 not found" == rv.json.get("message")


# TODO: Fix this
def test_get_comments_invalid_filing_error(session, client, jwt):
    """Assert that error is returned when filing doesn't exist."""
    with nested_session(session):
        b = factory_legal_entity("CP1111111")

        rv = client.get(
            f"/api/v2/businesses/{b.identifier}/filings/1/comments", headers=create_header(jwt, [STAFF_ROLE])
        )

        assert HTTPStatus.NOT_FOUND == rv.status_code
        assert "Filing 1 not found" == rv.json.get("message")


def test_get_comment_invalid_commentid_error(session, client, jwt):
    """Assert that error is returned when comment ID doesn't exist."""
    with nested_session(session):
        b = factory_legal_entity("CP1111111")
        f = factory_filing(b, ANNUAL_REPORT)

        rv = client.get(
            f"/api/v2/businesses/{b.identifier}/filings/{f.id}/comments/1", headers=create_header(jwt, [STAFF_ROLE])
        )

        assert HTTPStatus.NOT_FOUND == rv.status_code
        assert "Comment 1 not found" == rv.json.get("message")


def test_post_comment(session, client, jwt):
    """Assert that a simple post of a comment succeeds."""
    with nested_session(session):
        b = factory_legal_entity("CP1111111")
        f = factory_filing(b, ANNUAL_REPORT)

        json_data = copy.deepcopy(SAMPLE_JSON_DATA)
        json_data["comment"]["filingId"] = f.id

        rv = client.post(
            f"/api/v2/businesses/{b.identifier}/filings/{f.id}/comments",
            json=json_data,
            headers=create_header(jwt, [STAFF_ROLE]),
        )

        assert HTTPStatus.CREATED == rv.status_code


def test_post_comment_missing_filingid_error(session, client, jwt):
    """Assert that the post fails when missing filing ID in json (null and missing)."""
    with nested_session(session):
        b = factory_legal_entity("CP1111111")
        f = factory_filing(b, ANNUAL_REPORT)

        # test null filing ID
        json_data = copy.deepcopy(SAMPLE_JSON_DATA)
        json_data["comment"]["filingId"] = None

        rv = client.post(
            f"/api/v2/businesses/{b.identifier}/filings/{f.id}/comments",
            json=json_data,
            headers=create_header(jwt, [STAFF_ROLE]),
        )

        assert HTTPStatus.UNPROCESSABLE_ENTITY == rv.status_code

        # test missing filing ID
        json_data = copy.deepcopy(SAMPLE_JSON_DATA)
        del json_data["comment"]["filingId"]

        rv = client.post(
            f"/api/v2/businesses/{b.identifier}/filings/{f.id}/comments",
            json=json_data,
            headers=create_header(jwt, [STAFF_ROLE]),
        )

        assert HTTPStatus.UNPROCESSABLE_ENTITY == rv.status_code


def test_post_comment_missing_text_error(session, client, jwt):
    """Assert that the post fails when missing comment text in json (null and missing)."""
    with nested_session(session):
        b = factory_legal_entity("CP1111111")
        f = factory_filing(b, ANNUAL_REPORT)

        # test null comment text
        json_data = copy.deepcopy(SAMPLE_JSON_DATA)
        json_data["comment"]["comment"] = None

        rv = client.post(
            f"/api/v2/businesses/{b.identifier}/filings/{f.id}/comments",
            json=json_data,
            headers=create_header(jwt, [STAFF_ROLE]),
        )

        assert HTTPStatus.UNPROCESSABLE_ENTITY == rv.status_code

        # test missing comment text
        json_data = copy.deepcopy(SAMPLE_JSON_DATA)
        del json_data["comment"]["comment"]

        rv = client.post(
            f"/api/v2/businesses/{b.identifier}/filings/{f.id}/comments",
            json=json_data,
            headers=create_header(jwt, [STAFF_ROLE]),
        )

        assert HTTPStatus.UNPROCESSABLE_ENTITY == rv.status_code


def test_post_comment_basic_user_error(session, client, jwt):
    """Assert that the post fails when sent from Basic (non-staff) user."""
    with nested_session(session):
        b = factory_legal_entity("CP1111111")
        f = factory_filing(b, ANNUAL_REPORT)

        json_data = copy.deepcopy(SAMPLE_JSON_DATA)

        rv = client.post(
            f"/api/v2/businesses/{b.identifier}/filings/{f.id}/comments",
            json=json_data,
            headers=create_header(jwt, [BASIC_USER]),
        )

        assert HTTPStatus.UNAUTHORIZED == rv.status_code


def test_post_comment_mismatch_business_filing_error(session, client, jwt):
    """Assert that error is returned when filing isn't owned by business."""
    with nested_session(session):
        b = factory_legal_entity("CP1111111")
        b2 = factory_legal_entity("CP2222222")
        f = factory_filing(b, ANNUAL_REPORT)

        json_data = copy.deepcopy(SAMPLE_JSON_DATA)
        json_data["comment"]["filingId"] = f.id

        rv = client.post(
            f"/api/v2/businesses/{b2.identifier}/filings/{f.id}/comments",
            json=json_data,
            headers=create_header(jwt, [STAFF_ROLE]),
        )

        assert HTTPStatus.NOT_FOUND == rv.status_code
        assert f"Filing {f.id} not found" == rv.json.get("message")


def test_post_comment_invalid_business_error(session, client, jwt):
    """Assert that error is returned when business doesn't exist."""
    with nested_session(session):
        b = factory_legal_entity("CP1111111")
        f = factory_filing(b, ANNUAL_REPORT)

        json_data = copy.deepcopy(SAMPLE_JSON_DATA)
        json_data["comment"]["filingId"] = f.id

        rv = client.post(
            f"/api/v2/businesses/CP2222222/filings/{f.id}/comments",
            json=json_data,
            headers=create_header(jwt, [STAFF_ROLE]),
        )

        assert HTTPStatus.NOT_FOUND == rv.status_code
        assert "CP2222222 not found" == rv.json.get("message")


# TODO:Fix this
def test_post_comment_invalid_filing_error(session, client, jwt):
    """Assert that error is returned when filing doesn't exist."""
    with nested_session(session):
        b = factory_legal_entity("CP1111111")

        json_data = copy.deepcopy(SAMPLE_JSON_DATA)
        json_data["comment"]["filingId"] = 2

        rv = client.post(
            f"/api/v2/businesses/{b.identifier}/filings/2/comments",
            json=json_data,
            headers=create_header(jwt, [STAFF_ROLE]),
        )

        assert HTTPStatus.NOT_FOUND == rv.status_code
        assert "Filing 2 not found" == rv.json.get("message")


def test_post_comment_mismatch_filingid_error(session, client, jwt):
    """Assert that error is returned when filing ID in URL doesn't match filing ID in json."""
    with nested_session(session):
        b = factory_legal_entity("CP1111111")
        f = factory_filing(b, ANNUAL_REPORT)
        b2 = factory_legal_entity("CP2222222")
        f2 = factory_filing(b2, ANNUAL_REPORT)

        json_data = copy.deepcopy(SAMPLE_JSON_DATA)
        json_data["comment"]["filingId"] = f2.id

        rv = client.post(
            f"/api/v2/businesses/{b.identifier}/filings/{f.id}/comments",
            json=json_data,
            headers=create_header(jwt, [STAFF_ROLE]),
        )

        assert HTTPStatus.BAD_REQUEST == rv.status_code


def test_put_comment_error(session, client, jwt):
    """Assert that the PUT endpoint isn't allowed."""
    with nested_session(session):
        b = factory_legal_entity("CP1111111")
        f = factory_filing(b, ANNUAL_REPORT)
        c = factory_comment(b, f)

        json_data = copy.deepcopy(SAMPLE_JSON_DATA)
        json_data["comment"]["id"] = c.id
        json_data["comment"]["filingId"] = f.id

        rv = client.put(
            f"/api/v2/businesses/{b.identifier}/filings/{f.id}/comments/{c.id}",
            json=json_data,
            headers=create_header(jwt, [STAFF_ROLE]),
            follow_redirects=True,
        )

        assert HTTPStatus.METHOD_NOT_ALLOWED == rv.status_code


def test_delete_comment_error(session, client, jwt):
    """Assert that the DELETE endpoint isn't allowed."""
    with nested_session(session):
        b = factory_legal_entity("CP1111111")
        f = factory_filing(b, ANNUAL_REPORT)
        c = factory_comment(b, f)

        rv = client.delete(
            f"/api/v2/businesses/{b.identifier}/filings/{f.id}/comments/{c.id}",
            headers=create_header(jwt, [STAFF_ROLE]),
        )

        assert HTTPStatus.METHOD_NOT_ALLOWED == rv.status_code


def test_comments_in_filing_response(session, client, jwt):
    """Assert that the list of comments is the filing GET response."""
    with nested_session(session):
        b = factory_legal_entity("CP1111111")
        f = factory_filing(b, ANNUAL_REPORT)
        factory_comment(b, f, "comment 1")
        factory_comment(b, f, "comment 2")

        rv = client.get(f"/api/v2/businesses/{b.identifier}/filings/{f.id}", headers=create_header(jwt, [STAFF_ROLE]))

        assert rv.status_code == HTTPStatus.OK
        assert None is not rv.json["filing"]["header"].get("comments")
        assert 2 == len(rv.json["filing"]["header"].get("comments"))
