# Copyright © 2024 Province of British Columbia
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
"""This module is a wrapper for SFTP Connection object."""
from __future__ import annotations

import io
from enum import auto
from typing import Callable

import paramiko

from furnishings.utils.base import BaseEnum


class PublicKeyAlgorithms(BaseEnum):
    """Cipher types."""

    RSA = auto()
    ED25519 = auto()


class SftpConnection:
    """SFTP Connection object."""

    def __init__(  # pylint: disable=too-many-arguments
            self,
            host: str,
            port: int,
            username: str,
            password: str = None,
            private_key: str = None,
            private_key_passphrase: str = None,
            private_key_algorithm: str = PublicKeyAlgorithms.ED25519.value
    ):
        """Initialize the SFTP Connection object.

        Args:
            host (str): The hostname of the SFTP server.
            port (int): The port of the SFTP server.
            username (str): The username to use for the SFTP connection.
            password (str): The password to use for the SFTP connection.
            private_key (str): The private key to use for the SFTP connection.
            private_key_passphrase (str): The password for the private key.
            private_key_algorithm (str): The format of the private key.
        """
        self.host = host
        self.port = port
        self.username = username
        self.password = password
        self.private_key = private_key
        self.private_key_passphrase = private_key_passphrase
        self.private_key_algorithm = private_key_algorithm
        self.sftp_handler = None
        self.ssh_connection = None

    def __enter__(self) -> Callable:
        """Connect to the SFTP server.

        Returns:
            Connection: The SFTP Connection object.
        """
        try:
            self.ssh_connection = paramiko.SSHClient()
            self.ssh_connection.set_missing_host_key_policy(paramiko.AutoAddPolicy())
            if self.private_key:
                if self.private_key_algorithm == PublicKeyAlgorithms.RSA:
                    f__from_private_key = paramiko.RSAKey.from_private_key
                else:
                    f__from_private_key = paramiko.Ed25519Key.from_private_key

                if self.private_key_passphrase:
                    private_key = f__from_private_key(io.StringIO(self.private_key),
                                                      password=self.private_key_passphrase)
                else:
                    private_key = f__from_private_key(io.StringIO(self.private_key))

                self.ssh_connection.connect(hostname=self.host, port=self.port,
                                            username=self.username, pkey=private_key,
                                            key_filename=None, timeout=None,
                                            allow_agent=False, look_for_keys=False)
            else:
                self.ssh_connection.connect(hostname=self.host, port=self.port,
                                            username=self.username, password=self.password)

            self.sftp_handler = paramiko.SFTPClient.from_transport(self.ssh_connection.get_transport())

            print('sftp_connection successful')
            return self.sftp_handler
        except Exception as e:  # noqa: B902
            print(e)
            raise e

    def __exit__(self, exc_type, exc_value, traceback):
        """Close the SFTP Connection object."""
        if self.sftp_handler:
            self.sftp_handler.close()
            self.sftp_handler = None
        if self.ssh_connection:
            self.ssh_connection.close()
            self.ssh_connection = None
