# Copyright © 2020 Province of British Columbia
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

"""Tests to assure the AccountService jwt service integration."""
import json
import os
import random
import uuid
from http import HTTPStatus

import pytest
import requests
from flask import current_app

from business_account import AccountService


@pytest.mark.skipif(
    (os.getenv("RUN_JWT_INTEGRATION_TESTS", "false").lower() != "true"),
    reason="Integration tests are only run when requested."
)
def test_get_bearer_token_integration(app):
    with app.app_context():
        token = AccountService.get_bearer_token()

        assert token is not None
