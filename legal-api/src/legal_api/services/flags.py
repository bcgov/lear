# Copyright © 2019 Province of British Columbia
#
# Licensed under the Apache License, Version 2.0 (the 'License');
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an 'AS IS' BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
"""Manage the Feature Flags initialization, setup and service."""
import logging
from typing import Any, Optional

from flask import Flask
from ldclient import LDClient
from ldclient import get as ldclient_get
from ldclient import set_config as ldclient_set_config
from ldclient.config import Config
from ldclient.context import Context
from ldclient.integrations.test_data import TestData

from legal_api.models import User


class Flags:
    """Wrapper around the feature flag system.

    calls FAIL to FALSE

    If the feature flag service is unavailable
    AND
    there is no local config file
    Calls -> False

    """

    def __init__(self, app=None):
        """Initialize this object."""
        self.sdk_key = None
        self.app = None
        # Always have a logger, even before Flask app exists.
        self.logger = logging.getLogger(__name__)

        if app:
            self.init_app(app)

    def init_app(self, app: Flask, td: TestData = None):
        """Initialize the Feature Flag environment.
        Provide TD for TestData.
        """
        self.app = app
        self.sdk_key = app.config.get("LD_SDK_KEY")
        # Switch to Flask's logger once we have the app.
        self.logger = app.logger

        self.logger.info("starting feature flags init; has sdk key: %s, env: %s", bool(self.sdk_key), app.env)

        if td:
            client = LDClient(config=Config("testing", update_processor_class=td))

        elif self.sdk_key:
            ldclient_set_config(Config(self.sdk_key))
            client = ldclient_get()

        try:
            if client and client.is_initialized():
                app.extensions["featureflags"] = client
                app.teardown_appcontext(self.teardown)
        except Exception as err:
            app.logger.warning("Issue registering flag service %s", err)

    def teardown(self, exception):  # pylint: disable=unused-argument; flask method signature
        """Destroy all objects created by this extension."""
        client = self.app.extensions.get("featureflags") if self.app else None
        if client:
            client.close()

    def _get_client(self):
        if not self.app:
            return None

        try:
            return self.app.extensions["featureflags"]
        except KeyError:
            # Lazy-init if needed
            try:
                self.init_app(self.app)
                return self.app.extensions.get("featureflags")
            except Exception:
                return None

    @staticmethod
    def _get_anonymous_user():
        """Return a LaunchDarkly Context for anonymous evaluations."""
        return Context.create("anonymous")

    @staticmethod
    def _user_as_key(user: User):
        """Return a single-kind 'user' LD context with the user's key and attributes."""
        return Context.builder(user.sub) \
            .set("firstName", user.firstname) \
            .set("lastName", user.lastname) \
            .build()

    @staticmethod
    def _account_context(account_id: str) -> Context:
        """Return a single-kind 'account' LD context, keyed by the account id."""
        # Use Context.create(key, kind) to explicitly set non-default kind 'account'
        return Context.create(account_id, "account")

    def build_context(self, user: Optional[User], account_id: Optional[str]) -> Context:
        """Compose the appropriate LD context (single or multi) from user/account inputs.

        - user and account_id -> multi-context ('user' + 'account')
        - user only           -> single 'user' context
        - account_id only     -> single 'account' context
        - neither             -> anonymous 'user' context
        """
        if user and account_id:
            self.logger.debug("creating LD context with user and account_id")
            return Context.create_multi(
                Flags._user_as_key(user),
                Flags._account_context(account_id),
            )
        if user:
            self.logger.debug("creating LD context with user")
            return Flags._user_as_key(user)
        if account_id:
            self.logger.debug("creating LD context with account_id")
            return Flags._account_context(account_id)

        self.logger.debug("creating LD context with anonymous user")
        return Flags._get_anonymous_user()


    def is_on(self, flag: str, user: Optional[User] = None, account_id: Optional[str] = None) -> bool:
        """Assert that the flag is set for this user."""
        self.logger.debug("check if flag %s is on for user %s, account %s",
                                 flag, user.sub if user else "-", account_id)

        client = self._get_client()

        ctx = self.build_context(user, account_id)

        try:
            return bool(client.variation(flag, ctx, None))
        except Exception as err:
            self.logger.error(f"Unable to read flags: {err!r}", exc_info=True)
            return False

    def value(self, flag: str, user: Optional[User] = None, account_id: Optional[str] = None) -> Any:
        """Retrieve the value  of the (flag, user) tuple."""
        client = self._get_client()
        ctx = self.build_context(user, account_id)

        try:
            return client.variation(flag, ctx, None)
        except Exception as err:
            self.logger.error(f"Unable to read flags: {err!r}", exc_info=True)
            return False
