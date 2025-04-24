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
"""Tests to assure the meta end-point.

Test-Suite to ensure that the /meta endpoint is working as expected.
"""
from importlib.metadata import version


def test_meta_no_commit_hash(client):
    """Assert that the endpoint returns just the services __version__."""
    PACKAGE_NAME = "business_filer"
    ver = version(PACKAGE_NAME)
    framework_version = version("flask")

    rv = client.get("/meta/info")

    assert rv.status_code == 200
    assert rv.json == {
        "API": f"{PACKAGE_NAME}/{ver}",
        "FrameWork": f"{framework_version}",
    }


def test_meta_with_commit_hash(monkeypatch, client):
    """Assert that the endpoint return __version__ and the last git hash used to build the services image."""
    PACKAGE_NAME = "business_filer"
    ver = version(PACKAGE_NAME)
    framework_version = version("flask")

    commit_hash = "deadbeef_ha"
    monkeypatch.setenv("VCS_REF", commit_hash)

    rv = client.get("/meta/info")
    assert rv.status_code == 200
    assert rv.json == {
        "API": f"{PACKAGE_NAME}/{ver}-{commit_hash}",
        "FrameWork": f"{framework_version}",
    }