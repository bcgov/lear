# Copyright © 2023 Government of British Columbia
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
"""Feature flag wrapper for Flask."""
from __future__ import annotations

from contextlib import suppress
from typing import Union

import ldclient
from ldclient import LDClient, Config
from ldclient.integrations.test_data import TestData
from flask import current_app
from flask import has_app_context
from flask import Flask

import legal_api
# from legal_api.models import User
from legal_api.services.authz import get_role
from legal_api.utils.auth import JwtManager


class Flags():
    """Wrapper around the feature flag system.

    1 client per application.
    """

    COMPONENT_NAME = 'featureflags'

    def __init__(self, app: Flask = None):
        """Initialize this object."""
        self.sdk_key = None
        self.app = None

        if app:
            self.init_app(app)

    def init_app(self, app: Flask, td: TestData = None):
        """Initialize the Feature Flag environment.

        Provide TD for TestData.
        """
        self.app = app
        self.sdk_key = app.config.get('LD_SDK_KEY')

        if td:
            client = LDClient(config=Config('testing', update_processor_class=td))
        elif self.sdk_key:
            ldclient.set_config(Config(self.sdk_key))
            client = ldclient.get()

        # with suppress(Exception):
        try:
            if client and client.is_initialized():  # pylint: disable=E0601
                app.extensions[Flags.COMPONENT_NAME] = client
                app.teardown_appcontext(self.teardown)
        except Exception as err:  # noqa: B903
            if app and has_app_context():
                app.logger.warn('issue registering flag service', err)

    def teardown(self, exception):  # pylint: disable=unused-argument,no-self-use; flask method signature
        """Destroy all objects created by this extension.

        Ensure we close the client connection nicely.
        """
        with suppress(Exception):
            if client := current_app.extensions.get(Flags.COMPONENT_NAME):
                client.close()

    @staticmethod
    def get_client():
        """Get the currently configured ldclient."""
        with suppress(KeyError):
            client = current_app.extensions[Flags.COMPONENT_NAME]
            return client

        try:
            return ldclient.get()
        except Exception:  # noqa: B902
            return None

    @staticmethod
    def get_anonymous_user():
        """Return an anonymous key."""
        return {
            'key': 'anonymous'
        }

    @staticmethod
    def flag_user(user: legal_api.models.User,
                  account_id: int = None,
                  jwt: JwtManager = None):
        """Convert User into a Flag user dict."""
        if not isinstance(user, legal_api.models.User):
            return None

        _user = {
            'key': user.sub,
            'firstName': user.firstname,
            'lastName': user.lastname,
            'email': user.email,
            'custom': {
                'loginSource': user.login_source,
            }
        }
        with suppress(Exception):
            if account_id and jwt:
                _user['custom']['group'] = get_role(jwt, account_id)

        return _user

    @staticmethod
    def value(flag: str, user=None):
        """Retrieve the value  of the (flag, user) tuple."""
        client = Flags.get_client()

        if user:
            flag_user = user
        else:
            flag_user = Flags.get_anonymous_user()

        try:
            return client.variation(flag, flag_user, None)
        except Exception as err:  # noqa: B902
            current_app.logger.error('Unable to read flags: %s' % repr(err), exc_info=True)
            return None

    @staticmethod
    def detail(flag: str, user=None) -> Union[bool, int, str]:  # pylint: disable=E1136
        """Return the full flag and meta info."""
        client = current_app.extensions[Flags.COMPONENT_NAME]
        link = client.variation_detail(flag, user, False)
        return link
