#!/usr/bin/env python
# -*- coding: utf-8 -*-

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
"""s2i based launch script to run the service."""
import asyncio

from entity_filer.version import __version__
from entity_filer.service import run

if __name__ == '__main__':

    event_loop = asyncio.get_event_loop()
    event_loop.run_until_complete(run(event_loop))
    try:
        event_loop.run_forever()
    finally:
        event_loop.close()
