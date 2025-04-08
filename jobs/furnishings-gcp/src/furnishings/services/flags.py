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
"""Manage the Feature Flags initialization, setup and service.

NOTE: This is copied from search-api and altered a bit for legal-api.
This will be reworked and moved to a common service later."""
import json
from contextlib import suppress

import ldclient
from flask import Flask, current_app
from ldclient import Config, Context, LDClient
from ldclient.integrations.test_data import TestData


class Flags():
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
            with open('flags.json', 'r') as file:
                data = file.read()
                test_flags: dict[str, dict] = json.loads(data)
                for flag_name, flag_value in test_flags['flagValues'].items():
                    # NOTE: should check if isinstance dict and if so, apply each variation
                    td.update(td.flag(flag_name).variation_for_all(flag_value))

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
            return ldclient.get()
        except Exception:
            return None

    @staticmethod
    def get_anonymous_user():
        """Return an anonymous key."""
        return {"key": "anonymous"}

    @staticmethod
    def is_on(flag: str, user: dict = None) -> bool:
        """Assert that the flag is set for this user."""
        try:
            return bool(Flags.value(flag, user))
        except Exception as err:
            current_app.logger.error('Unable to read flags: %s' % repr(err), exc_info=True)
            return False

    @staticmethod
    def value(flag: str, user: dict = None):
        """Retrieve the value  of the (flag, user) tuple."""
        try:
            client = Flags.get_client()
            flag_user = user if user else Flags.get_anonymous_user()
            flag_context = Context.from_dict({**flag_user, "kind": "user"})
            return client.variation(flag, flag_context, None)
        except Exception as err:
            current_app.logger.error("Unable to read flags: %s", repr(err), exc_info=True)
            return None
