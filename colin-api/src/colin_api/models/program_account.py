# Copyright © 2022 Province of British Columbia
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
"""Program account details from BNI DB link."""
from __future__ import annotations

from typing import Dict, Optional

from flask import current_app

from colin_api.resources.db import DB


class ProgramAccount:  # pylint: disable=too-many-instance-attributes; need all these fields
    """Class to contain all model-like to get from database.

    PROGRAM_ACCOUNT_PK                        NOT NULL NUMBER(9)
    BUSINESS_NO                               NOT NULL NUMBER(9)
    BUSINESS_PROGRAM_ID                       NOT NULL VARCHAR2(2)
    PROGRAM_ACCOUNT_REF_NO                    NOT NULL NUMBER(4)
    SBN_PARTNER_PK                            NOT NULL NUMBER(9)
    SBN_PROGRAM_TYPE                          NOT NULL NUMBER(4)
    CROSS_REFERENCE_PROGRAM_NO                NOT NULL VARCHAR2(10)
    SUCCESSOR_PROGRAM_ACCOUNT_PK                       NUMBER(9)
    TRANSACTION_TMSTMP                        NOT NULL TIMESTAMP(6)
    TRANSACTION_ID                            NOT NULL VARCHAR2(15)
    """

    business_no = None
    business_program_id = None
    program_account_ref_no = None
    sbn_program_type = None
    cross_reference_program_no = None
    transaction_tmstmp = None
    transaction_id = None

    def __init__(self):
        """Initialize with all values None."""

    def as_dict(self) -> Dict:
        """Return dict version of self."""
        return {
            'business_no': self.business_no,
            'business_program_id': self.business_program_id,
            'program_account_ref_no': self.program_account_ref_no,
            'sbn_program_type': self.sbn_program_type,
            'cross_reference_program_no': self.cross_reference_program_no,
            'transaction_tmstmp': self.transaction_tmstmp,
            'transaction_id': self.transaction_id
        }

    @classmethod
    def get_program_account(cls, transaction_id=None,
                            cross_reference_program_no=None, con=None) -> Optional[ProgramAccount]:
        """Get program account.

        transaction_id or cross_reference_program_no is required. only one will be considered.
        """
        if not transaction_id and not cross_reference_program_no:
            return None

        try:
            bni_db_link = current_app.config.get('ORACLE_BNI_DB_LINK')
            if not con:
                con = DB.connection

            where = ''
            # get data with transaction_id if available
            if transaction_id:
                where = f"transaction_id = '{transaction_id}'"
            elif cross_reference_program_no:
                where = f"cross_reference_program_no = '{cross_reference_program_no}'"

            cursor = con.cursor()
            cursor.execute(
                f"""SELECT
                  business_no,
                  business_program_id,
                  program_account_ref_no,
                  sbn_program_type,
                  cross_reference_program_no,
                  transaction_tmstmp,
                  transaction_id
                FROM program_account@{bni_db_link}
                WHERE {where}
                """
            )
            data = cursor.fetchone()
            if not data:
                return None

            # add column names to resultset to build out correct json structure and make manipulation below more robust
            # (better than column numbers)
            data = dict(zip([x[0].lower() for x in cursor.description], data))

            # convert to ProgramAccount object
            program_account = ProgramAccount()
            program_account.business_no = data['business_no']
            program_account.business_program_id = data['business_program_id']
            program_account.program_account_ref_no = data['program_account_ref_no']
            program_account.sbn_program_type = data['sbn_program_type']
            program_account.cross_reference_program_no = data['cross_reference_program_no']
            program_account.transaction_tmstmp = data['transaction_tmstmp']
            program_account.transaction_id = data['transaction_id']
            return program_account
        except Exception as err:
            current_app.logger.error(f'Error in ProgramAccount: Failed to collect program_account@{bni_db_link} ' +
                                     f'for {transaction_id or cross_reference_program_no}')
            raise err

    @classmethod
    def get_bn15s(cls, identifiers: list = None, con=None) -> list:
        """Get BN15s."""
        if not identifiers:
            return []

        try:
            bni_db_link = current_app.config.get('ORACLE_BNI_DB_LINK')
            if not con:
                con = DB.connection

            identifiers_str = "', '".join(identifiers)

            cursor = con.cursor()
            cursor.execute(
                f"""SELECT
                  business_no,
                  business_program_id,
                  program_account_ref_no,
                  sbn_program_type,
                  cross_reference_program_no,
                  transaction_tmstmp,
                  transaction_id
                FROM program_account@{bni_db_link}
                WHERE cross_reference_program_no in ('{identifiers_str}')
                """
            )
            data = cursor.fetchall()

            results = []
            for row in data:
                row = dict(zip([x[0].lower() for x in cursor.description], row))
                program_account_ref_no = str(row['program_account_ref_no']).zfill(4)
                bn15 = f"{row['business_no']}{row['business_program_id']}{program_account_ref_no}"
                results.append({row['cross_reference_program_no']: bn15})

            return results

        except Exception as err:
            current_app.logger.error(f'Error in ProgramAccount: Failed to collect program_account@{bni_db_link} ' +
                                     f'for {identifiers}')
            raise err
