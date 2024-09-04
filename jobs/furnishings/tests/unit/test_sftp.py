# Copyright © 2024 Province of British Columbia
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
from io import StringIO
from os import path


def test_get(sftpserver, sftpconnection):
    """Assert a file can be retrieved to the server."""
    file_content = "content"
    server_dir = 'dir'
    file_name = 'test_file.txt'

    with sftpserver.serve_content({server_dir: {file_name: file_content}}):
        with sftpconnection as sftpclient:
            with sftpclient.open(path.join(server_dir, file_name)) as file:
                assert file.read().decode() == file_content

def test_put(tmp_path, sftpserver, sftpconnection):
    """Assert a file can be uploaded to the server."""
    file_content = "content"
    server_dir = 'dir'
    file_name = 'test_file.txt'

    file_path = tmp_path / file_name
    file_path.write_text(file_content)

    with sftpserver.serve_content({server_dir: {}}):
        with sftpconnection as sftpclient:
            sftpclient.put(file_path, path.join(server_dir, file_name))
            with sftpclient.open(path.join(server_dir, file_name)) as file:
                assert file.read().decode() == file_content

def test_putfo(sftpserver, sftpconnection):
    """Assert the contents of a file object can be uploaded to the server."""
    file_content = "content"
    server_dir = 'dir'
    file_name = 'test_file.txt'

    with sftpserver.serve_content({server_dir: {}}):
        with sftpconnection as sftpclient:
            sftpclient.putfo(StringIO(file_content), path.join(server_dir, file_name))
            with sftpclient.open(path.join(server_dir, file_name)) as file:
                assert file.read().decode() == file_content