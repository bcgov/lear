# Copyright © 2023 Province of British Columbia
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
"""This module provides Queue type services."""
from __future__ import annotations

import base64
import json
from concurrent.futures import TimeoutError  # pylint: disable=W0622
from concurrent.futures import CancelledError
from contextlib import suppress
from typing import Optional

from flask import Flask, current_app
from google.auth import jwt
from google.cloud import pubsub_v1
from simple_cloudevent import (
    CloudEventVersionException,
    InvalidCloudEventError,
    SimpleCloudEvent,
    from_queue_message,
    to_queue_message,
)
from werkzeug.local import LocalProxy


class GcpQueue:
    """Provides Queue type services"""

    def __init__(self, app: Flask = None):
        """Initializes the GCP Queue class"""
        self.audience = None
        self.credentials_pub = None
        self.gcp_auth_key = None
        self.publisher_audience = None
        self.service_account_info = None
        self._publisher = None

        if app:
            self.init_app(app)

    def init_app(self, app: Flask):
        """Initializes the application"""
        self.gcp_auth_key = app.config.get("GCP_AUTH_KEY")
        if self.gcp_auth_key:
            try:
                audience = current_app.config.get(
                    "AUDIENCE",
                    "https://pubsub.googleapis.com/google.pubsub.v1.Subscriber",
                )
                publisher_audience = current_app.config.get(
                    "PUBLISHER_AUDIENCE",
                    "https://pubsub.googleapis.com/google.pubsub.v1.Publisher",
                )

                self.service_account_info = json.loads(base64.b64decode(self.gcp_auth_key).decode("utf-8"))
                credentials = jwt.Credentials.from_service_account_info(self.service_account_info, audience=audience)
                self.credentials_pub = credentials.with_claims(audience=publisher_audience)
            except Exception as error:  # noqa: B902
                raise Exception("Unable to create a connection", error) from error  # pylint: disable=W0719

    @property
    def publisher(self):
        """Returns the publisher"""
        if not self._publisher and self.credentials_pub:
            self._publisher = pubsub_v1.PublisherClient(credentials=self.credentials_pub)
        else:
            self._publisher = pubsub_v1.PublisherClient()
        return self._publisher

    @staticmethod
    def is_valid_envelope(msg: dict):
        """Checks if the envelope is valid"""
        if (
            msg.get("subscription")
            and (message := msg.get("message"))
            and isinstance(message, dict)
            and message.get("data")
        ):
            return True
        return False

    @staticmethod
    def get_envelope(request: LocalProxy) -> Optional[dict]:
        """Returns the envelope"""
        with suppress(Exception):
            if (envelope := request.get_json()) and GcpQueue.is_valid_envelope(envelope):
                return envelope
        return None

    @staticmethod
    def get_simple_cloud_event(request: LocalProxy, return_raw: bool = False) -> type[SimpleCloudEvent | dict | None]:
        """Return a SimpleCloudEvent if one is in session from the PubSub call.
        Parameters
        ------------
            request: LocalProxy
                An active Flask request object
            return_raw: bool, Optional = False
                Flag to return the raw data on error, if it exists
        Return
        -----------
            ce_returned: boolean
                if a ce is returned == True
            SimpleCloudEvent |
            dict |
            None
                the second value returned is either a:
                SimpleCloudEvent -or-
                None - if there is no SimpleCloudEvent
                dict - if return_raw was set to true and it's not a SimpleCloudEvent -or-
        """
        if not (envelope := GcpQueue.get_envelope(request)):
            return None

        if (
            (message := envelope.get("message"))
            and (raw_data := message.get("data"))
            and (str_data := base64.b64decode(raw_data))
        ):
            try:
                return from_queue_message(str_data)
            except (
                CloudEventVersionException,
                InvalidCloudEventError,
                ValueError,
                Exception,
            ):
                if return_raw and str_data:
                    return str_data
        return None

    def publish(self, topic: str, payload: bytes):
        """Send payload to the queue."""
        if not (publisher := self.publisher):
            raise Exception("missing setup arguments")  # pylint: disable=W0719

        try:
            future = publisher.publish(topic, payload)

            return future.result()
        except (CancelledError, TimeoutError) as error:
            raise Exception("Unable to post to queue", error) from error  # pylint: disable=W0719

    @staticmethod
    def to_queue_message(ce: SimpleCloudEvent):
        """Return a byte string, of the CloudEvent in JSON format"""
        return to_queue_message(ce)

    @staticmethod
    def from_queue_message(data: dict):
        """Convert a queue message back to a simple CloudEvent"""
        return from_queue_message(data)
