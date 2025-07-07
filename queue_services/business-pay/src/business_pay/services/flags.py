# Copyright © 2025 Province of British Columbia
#
# Licensed under the BSD 3 Clause License, (the "License");
# you may not use this file except in compliance with the License.
# The template for the license can be found here
#    https://opensource.org/license/bsd-3-clause/
#
# Redistribution and use in source and binary forms,
# with or without modification, are permitted provided that the
# following conditions are met:
#
# 1. Redistributions of source code must retain the above copyright notice,
#    this list of conditions and the following disclaimer.
#
# 2. Redistributions in binary form must reproduce the above copyright notice,
#    this list of conditions and the following disclaimer in the documentation
#    and/or other materials provided with the distribution.
#
# 3. Neither the name of the copyright holder nor the names of its contributors
#    may be used to endorse or promote products derived from this software
#    without specific prior written permission.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS “AS IS”
# AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO,
# THE IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE
# ARE DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT HOLDER OR CONTRIBUTORS BE
# LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR
# CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF
# SUBSTITUTE GOODS OR SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS
# INTERRUPTION) HOWEVER CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN
# CONTRACT, STRICT LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE)
# ARISING IN ANY WAY OUT OF THE USE OF THIS SOFTWARE, EVEN IF ADVISED OF THE
# POSSIBILITY OF SUCH DAMAGE.
"""Manage the Feature Flags initialization, setup and service."""
from flask import current_app
from ldclient import get as ldclient_get  # noqa: I001
from ldclient import set_config as ldclient_set_config
from ldclient.config import Config  # noqa: I005
from ldclient.context import Context
from ldclient.integrations import Files
from ldclient.interfaces import UpdateProcessor


class FileDataSource(UpdateProcessor):
    """FileDataStore has been removed, so this provides similar functionality."""

    @classmethod
    def factory(cls, **kwargs):
        """Provide a way to use local files as a source of feature flag state."""
        return lambda config, store, ready: Files.new_data_source(
            paths=kwargs.get("paths"),
            auto_update=kwargs.get("auto_update", False),
            poll_interval=kwargs.get("poll_interval", 1),
            force_polling=kwargs.get("force_polling", False),
        )(config, store, ready)


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

        if app:
            self.init_app(app)

    def init_app(self, app):
        """Initialize the Feature Flag environment."""
        self.app = app
        self.sdk_key = app.config.get("LD_SDK_KEY")

        environment = app.config.get("ENVIRONMENT")

        if self.sdk_key or environment != "production":

            if environment == "production":
                config = Config(sdk_key=self.sdk_key)
            else:
                factory = FileDataSource.factory(paths=["flags.json"], auto_update=True)
                config = Config(
                    sdk_key=self.sdk_key,
                    update_processor_class=factory,
                    send_events=False,
                )

            ldclient_set_config(config)
            client = ldclient_get()

            app.extensions["featureflags"] = client

    def teardown(
        self, exception
    ):  # pylint: disable=unused-argument; flask method signature
        """Destroy all objects created by this extension."""
        client = current_app.extensions["featureflags"]
        client.close()

    def _get_client(self):
        try:
            client = current_app.extensions["featureflags"]
        except KeyError:
            try:
                self.init_app(current_app)
                client = current_app.extensions["featureflags"]
            except KeyError:
                client = None

        return client

    @staticmethod
    def _get_anonymous_user():
        return Context.create("anonymous")

    @staticmethod
    def _user_as_key(user):
        return (
            Context.builder(user.sub)
            .set("firstName", user.firstname)
            .set("lastName", user.lastname)
            .build()
        )

    def is_on(self, flag: str, user=None) -> bool:
        """Assert that the flag is set for this user."""
        client = self._get_client()

        if user:
            flag_user = self._user_as_key(user)
        else:
            flag_user = self._get_anonymous_user()

        try:
            return bool(client.variation(flag, flag_user, None))
        except Exception as err:
            current_app.logger.error(
                "Unable to read flags: %s" % repr(err), exc_info=True
            )
            return False

    def value(self, flag: str, user=None) -> bool:
        """Retrieve the value  of the (flag, user) tuple."""
        client = self._get_client()

        if user:
            flag_user = self._user_as_key(user)
        else:
            flag_user = self._get_anonymous_user()

        try:
            user_context = Context.builder(flag_user).build()
            return client.variation(flag, user_context, None)
        except Exception as err:
            current_app.logger.error(
                "Unable to read flags: %s" % repr(err), exc_info=True
            )
            return False
