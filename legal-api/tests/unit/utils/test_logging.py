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

"""Tests to assure the logging utilities.

Test-Suite to ensure that the logging setup is working as expected.
"""

import os

from legal_api.utils.logging import setup_logging


def test_logging_with_file(capsys):
    """Assert that logging is setup with the configuration file."""
    file_path = os.path.join(os.path.abspath(os.path.dirname(__file__)), "logging.conf")
    setup_logging(file_path)  # important to do this first

    captured = capsys.readouterr()

    assert captured.out.startswith("Configure logging, from conf")


def test_logging_with_missing_file(capsys):
    """Assert that a message is sent to STDERR when the configuration doesn't exist."""
    file_path = None
    setup_logging(file_path)  # important to do this first

    captured = capsys.readouterr()

    assert captured.err.startswith("Unable to configure logging")
