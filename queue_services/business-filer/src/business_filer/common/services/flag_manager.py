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
from __future__ import annotations

from contextlib import suppress
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from ldclient.integrations.test_data import TestData

import ldclient
from flask import Flask, current_app
from ldclient import Config, Context, LDClient


class Flags:
    """Wrapper around the feature flag system.
    calls FAIL to FALSE
    If the feature flag service is unavailable
    AND
    there is no local config file
    Calls -> False
    """

    COMPONENT_NAME = "featureflags"

    def __init__(self, app=None):
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
        self.sdk_key = app.config.get("LD_SDK_KEY")
        if td:
            client = LDClient(config=Config("testing", update_processor_class=td))

        elif self.sdk_key:
            ldclient.set_config(Config(self.sdk_key))
            client = ldclient.get()

        try:
            if client and client.is_initialized():
                app.extensions[Flags.COMPONENT_NAME] = client
                app.teardown_appcontext(self.teardown)
        except Exception as err:
            app.logger.warning("Issue registering flag service %s", err)

    def teardown(self, exception):
        """Destroy all objects created by this extension.
        Ensure we close the client connection nicely.
        """
        with suppress(Exception):
            if client := current_app.extensions.get(Flags.COMPONENT_NAME):
                client.close()

    @staticmethod
    def get_client() -> LDClient:
        """Get the currently configured ldclient."""
        with suppress(KeyError):
            client = current_app.extensions[Flags.COMPONENT_NAME]
            return client
        try:
            current_app.logger.warning("No LDClient found, using default client.")
            return ldclient.get()
        except Exception:
            return None

    @staticmethod
    def get_anonymous_user():
        """Return an anonymous key."""
        return {"key": "anonymous"}

    @staticmethod
    def is_on(flag: str, user: dict | None = None) -> bool:
        """Assert that the flag is set for this user."""
        try:
            return bool(Flags.value(flag, user))
        except Exception as err:
            current_app.logger.error("Unable to read flags: %s", repr(err), exc_info=True)
            return False

    @staticmethod
    def value(flag: str, user: dict | None = None):
        """Retrieve the value  of the (flag, user) tuple."""
        try:
            client = Flags.get_client()
            flag_user = user if user else Flags.get_anonymous_user()
            flag_context = Context.from_dict({**flag_user, "kind": "user"})
            return client.variation(flag, flag_context, None)
        except Exception as err:
            current_app.logger.error("Unable to read flags: %s", repr(err), exc_info=True)
            return None
