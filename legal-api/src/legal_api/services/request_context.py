# Copyright © 2025 Province of British Columbia
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
"""Helpers to build and access a per-request RequestContext."""
from dataclasses import dataclass

from flask import g, has_request_context, request

from business_model.models import User


@dataclass(frozen=True)
class RequestContext:
    account_id: str | None = None
    user: User | None = None
    account_linking_key: str | None = None


def build_from_flask() -> RequestContext:
    """Build a RequestContext from the active Flask request, if any."""
    if not has_request_context():
        return RequestContext()

    # Account header (configurable)
    account_id = request.headers.get("Account-Id", None)

    account_linking_key = request.headers.get("Account-Linking-Key", None)

    # Token info and user
    token_info = getattr(g, "jwt_oidc_token_info", None)
    user = User.get_or_create_user_by_jwt(token_info) if token_info else None

    return RequestContext(
        account_id=account_id,
        user=user,
        account_linking_key=account_linking_key,
    )


def get_request_context() -> RequestContext:
    """Get (or lazily create) the RequestContext for the current request."""
    if not has_request_context():
        return RequestContext()
    rc = getattr(g, "request_context", None)
    if rc is None:
        rc = build_from_flask()
        g.request_context = rc
    return rc


def add_account_linking_key_header(headers: dict) -> None:
    """Forward the incoming Account-Linking-Key header to an outgoing auth-api/pay-api call, if present."""
    if not has_request_context():
        return

    if account_linking_key := request.headers.get("Account-Linking-Key"):
        headers["Account-Linking-Key"] = account_linking_key
