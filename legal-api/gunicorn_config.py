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
"""The configuration for gunicorn, which picks up the
runtime options from environment variables
"""

import os
import gunicorn_server

# https://docs.gunicorn.org/en/stable/settings.html#workers
workers = int(os.environ.get("GUNICORN_PROCESSES", "1"))  # gunicorn default - 1
worker_class = os.environ.get("GUNICORN_WORKER_CLASS", "sync")  # gunicorn default - sync
worker_connections = int(os.environ.get("GUNICORN_WORKER_CONNECTIONS", "1000"))  # gunicorn default - 1000
threads = int(os.environ.get("GUNICORN_THREADS", "3"))  # gunicorn default - 1
timeout = int(os.environ.get("GUNICORN_TIMEOUT", "100"))  # gunicorn default - 30
keepalive = int(os.environ.get("GUNICORN_KEEPALIVE", "2"))  # gunicorn default - 2
# WHEN MIGRATING TO GCP -  GUNICORN_THREADS = 8, GUNICORN_TIMEOUT = 0, GUNICORN_PROCESSES = 1


forwarded_allow_ips = "*"  # pylint: disable=invalid-name
secure_scheme_headers = {"X-Forwarded-Proto": "https"}  # pylint: disable=invalid-name

# Server Hooks
pre_fork = gunicorn_server.pre_fork
post_fork = gunicorn_server.post_fork
worker_exit = gunicorn_server.worker_exit
