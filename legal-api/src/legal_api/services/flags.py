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
from typing import Optional, Any
from ldclient import get as ldclient_get, set_config as ldclient_set_config  # noqa: I001
from ldclient.config import Config  # noqa: I005
from ldclient.context import Context
from ldclient.impl.integrations.files.file_data_source import _FileDataSource
from ldclient.interfaces import UpdateProcessor

from legal_api.models import User


class FileDataSource(UpdateProcessor):
    """FileDataStore has been removed, so this provides similar functionality."""

    @classmethod
    def factory(cls, **kwargs):
        """Provide a way to use local files as a source of feature flag state.

        .. deprecated:: 6.8.0
          This module and this implementation class are deprecated and may be changed or removed in the future.
          Please use :func:`ldclient.integrations.Files.new_data_source()`.

        The keyword arguments are the same as the arguments to :func:`ldclient.integrations.Files.new_data_source()`.
        """
        return lambda config, store, ready: _FileDataSource(store, ready,
                                                            paths=kwargs.get('paths'),
                                                            auto_update=kwargs.get('auto_update', False),
                                                            poll_interval=kwargs.get('poll_interval', 1),
                                                            force_polling=kwargs.get('force_polling', False))


class Flags():
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

    def init_app(self, app):
        """Initialize the Feature Flag environment."""
        self.app = app
        self.sdk_key = app.config.get('LD_SDK_KEY')
        # Switch to Flask's logger once we have the app.
        self.logger = app.logger

        self.logger.info('starting feature flags init; has sdk key: %s, env: %s', bool(self.sdk_key), app.env)

        if self.sdk_key or app.env != 'production':
            self.logger.debug("sdk key used: %s", self.sdk_key)

            if app.env == 'production':
                config = Config(sdk_key=self.sdk_key)
            else:
                factory = FileDataSource.factory(paths=['flags.json'],
                                                 auto_update=True)
                config = Config(sdk_key=self.sdk_key,
                                update_processor_class=factory,
                                send_events=False)

            ldclient_set_config(config)
            client = ldclient_get()

            app.extensions['featureflags'] = client

    def teardown(self, exception):  # pylint: disable=unused-argument; flask method signature
        """Destroy all objects created by this extension."""
        client = self.app.extensions.get('featureflags') if self.app else None
        if client:
            client.close()

    def _get_client(self):
        if not self.app:
            return None

        try:
            return self.app.extensions['featureflags']
        except KeyError:
            # Lazy-init if needed
            try:
                self.init_app(self.app)
                return self.app.extensions.get('featureflags')
            except Exception:
                return None

    @staticmethod
    def _get_anonymous_user():
        """Return a LaunchDarkly Context for anonymous evaluations."""
        return Context.create('anonymous')

    @staticmethod
    def _user_as_key(user: User):
        """Return a single-kind 'user' LD context with the user's key and attributes."""
        return Context.builder(user.sub) \
            .set('firstName', user.firstname) \
            .set('lastName', user.lastname) \
            .build()

    @staticmethod
    def _account_context(account_id: str) -> Context:
        """Return a single-kind 'account' LD context, keyed by the account id."""
        # Use Context.create(key, kind) to explicitly set non-default kind 'account'
        return Context.create(account_id, 'account')

    def build_context(self, user: Optional[User], account_id: Optional[str]) -> Context:
        """Compose the appropriate LD context (single or multi) from user/account inputs.

        - user and account_id -> multi-context ('user' + 'account')
        - user only           -> single 'user' context
        - account_id only     -> single 'account' context
        - neither             -> anonymous 'user' context
        """
        if user and account_id:
            self.logger.debug('creating LD context with user and account_id')
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
        self.logger.debug('check if flag %s is on for user %s, account %s',
                                 flag, user.sub if user else '-', account_id)

        client = self._get_client()

        ctx = self.build_context(user, account_id)

        try:
            return bool(client.variation(flag, ctx, None))
        except Exception as err:
            self.logger.error('Unable to read flags: %s' % repr(err), exc_info=True)
            return False

    def value(self, flag: str, user: Optional[User] = None, account_id: Optional[str] = None) -> Any:
        """Retrieve the value  of the (flag, user) tuple."""
        client = self._get_client()
        ctx = self.build_context(user, account_id)

        try:
            return client.variation(flag, ctx, None)
        except Exception as err:
            self.logger.error('Unable to read flags: %s' % repr(err), exc_info=True)
            return False
