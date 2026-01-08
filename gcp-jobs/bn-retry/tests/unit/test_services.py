# Copyright © 2025 Province of British Columbia
#
# Licensed under the BSD 3 Clause License, (the "License");
# you may not use this file except in compliance with the License.
# The template for the license can be found here
#    https://opensource.org/license/bsd-3-clause/
"""Unit tests for services module."""

from http import HTTPStatus

import pytest
import requests_mock

from bn_retry import create_app
from bn_retry.services import check_bn15_status_batch, get_bearer_token


def test_get_bearer_token_success(app):
    """Test successful bearer token retrieval."""
    with requests_mock.Mocker() as m:
        m.post(app.config.get("ACCOUNT_SVC_AUTH_URL"), json={"access_token": "test_token_123"})

        token = get_bearer_token(20)

        assert token == "test_token_123"


def test_get_bearer_token_failure(app):
    """Test bearer token retrieval failure."""
    with requests_mock.Mocker() as m:
        m.post(app.config.get("ACCOUNT_SVC_AUTH_URL"), status_code=HTTPStatus.UNAUTHORIZED)

        token = get_bearer_token(20)

        assert token is None


def test_check_bn15_status_batch_success(app):
    """Test batch BN15 check success."""
    with requests_mock.Mocker() as m:
        # Mock auth token
        m.post(app.config.get("ACCOUNT_SVC_AUTH_URL"), json={"access_token": "test_token"})

        # Mock Colin API batch response
        colin_url = f"{app.config.get('COLIN_API_URL')}{app.config.get('COLIN_API_VERSION')}/programAccount/check-bn15s"
        m.post(colin_url, json={"bn15s": [{"FM123": "123456789BC0001", "FM456": "123456789BC0002"}]})

        results = check_bn15_status_batch(["FM123", "FM456"])

        assert len(results) == 1
        assert results[0]["FM123"] == "123456789BC0001"


def test_check_bn15_status_batch_empty_response(app):
    """Test batch BN15 check with empty response."""
    with requests_mock.Mocker() as m:
        m.post(app.config.get("ACCOUNT_SVC_AUTH_URL"), json={"access_token": "test_token"})

        colin_url = f"{app.config.get('COLIN_API_URL')}{app.config.get('COLIN_API_VERSION')}/programAccount/check-bn15s"
        m.post(colin_url, json={"bn15s": []})

        results = check_bn15_status_batch(["FM123"])

        assert results == []
