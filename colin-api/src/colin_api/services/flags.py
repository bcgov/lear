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
from ldclient import get as ldclient_get, set_config as ldclient_set_config  # noqa: I001
from ldclient.config import Config  # noqa: I005
from ldclient.impl.integrations.files.file_data_source import _FileDataSource
from ldclient.interfaces import UpdateProcessor


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

        if app:
            self.init_app(app)

    def init_app(self, app):
        """Initialize the Feature Flag environment."""
        self.app = app
        self.sdk_key = app.config.get('LD_SDK_KEY')

        if self.sdk_key or app.env != 'production':

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
