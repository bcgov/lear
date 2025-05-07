# Copyright © 2019 Province of British Columbia
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#     http://www.apache.org/licenses/LICENSE-2.0
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License
"""Filings are legal documents that alter the state of a business."""
# pylint: disable=too-many-lines
import copy
from contextlib import suppress
from datetime import date, datetime, timezone
from enum import Enum
from http import HTTPStatus
from typing import Final, List

from sqlalchemy import and_, desc, event, func, inspect, not_, or_, select
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.ext.hybrid import hybrid_property
from sqlalchemy.orm import backref

from legal_api.exceptions import BusinessException
from legal_api.models.colin_event_id import ColinEventId
from legal_api.schemas import rsbc_schemas
from legal_api.utils.util import build_schema_error_response

from .db import db  # noqa: I001


from .comment import Comment  # noqa: I001,F401,I003 pylint: disable=unused-import; needed by SQLAlchemy relationship


class Filing(db.Model):  # pylint: disable=too-many-instance-attributes,too-many-public-methods
    # allowing the model to be deep.
    """Immutable filing record.

    Manages the filing ledger for the associated business.
    """

    class TempCorpFilingType(str, Enum):
        """Render enum of temporary corporation filing types."""

        AMALGAMATION = 'amalgamationApplication'
        CONTINUATION_IN = 'continuationIn'
        INCORPORATION = 'incorporationApplication'
        REGISTRATION = 'registration'

    class Status(str, Enum):
        """Render an Enum of the Filing Statuses."""

        COMPLETED = 'COMPLETED'
        CORRECTED = 'CORRECTED'
        DRAFT = 'DRAFT'
        EPOCH = 'EPOCH'
        ERROR = 'ERROR'
        PAID = 'PAID'
        PENDING = 'PENDING'
        PENDING_CORRECTION = 'PENDING_CORRECTION'
        WITHDRAWN = 'WITHDRAWN'

        TOMBSTONE = 'TOMBSTONE'

        # filings with staff review
        APPROVED = 'APPROVED'
        AWAITING_REVIEW = 'AWAITING_REVIEW'
        CHANGE_REQUESTED = 'CHANGE_REQUESTED'
        REJECTED = 'REJECTED'

    class Source(Enum):
        """Render an Enum of the Filing Sources."""

        BTR = 'BTR'
        COLIN = 'COLIN'
        LEAR = 'LEAR'

    # TODO: get legal types from defined class once table is made (getting it from Business causes circ import)
    # TODO: add filing types for btr
    FILINGS = {
        'affidavit': {
            'name': 'affidavit',
            'title': 'Affidavit',
            'codes': {
                'CP': 'AFDVT'
            }
        },
        'agmExtension': {
            'name': 'agmExtension',
            'title': 'AGM Extension',
            'codes': {
                'BC': 'AGMDT',
                'BEN': 'AGMDT',
                'ULC': 'AGMDT',
                'CC': 'AGMDT',
                'C': 'AGMDT',
                'CBEN': 'AGMDT',
                'CUL': 'AGMDT',
                'CCC': 'AGMDT'
            }
        },
        'agmLocationChange': {
            'name': 'agmLocationChange',
            'title': 'AGM Change of Location',
            'codes': {
                'BC': 'AGMLC',
                'BEN': 'AGMLC',
                'ULC': 'AGMLC',
                'CC': 'AGMLC',
                'C': 'AGMLC',
                'CBEN': 'AGMLC',
                'CUL': 'AGMLC',
                'CCC': 'AGMLC'
            }
        },
        'alteration': {
            'name': 'alteration',
            'title': 'Notice of Alteration Filing',
            'codes': {
                'BC': 'ALTER',
                'BEN': 'ALTER',
                'ULC': 'ALTER',
                'CC': 'ALTER',
                'C': 'ALTER',
                'CBEN': 'ALTER',
                'CUL': 'ALTER',
                'CCC': 'ALTER',
                'BC_TO_ULC': 'NOALU',
                'C_TO_CUL': 'NOALU'
            }
        },
        'amalgamationApplication': {
            'name': 'amalgamationApplication',
            'temporaryCorpTypeCode': 'ATMP',
            'regular': {
                'name': 'regularAmalgamation',
                'title': 'Amalgamation Application (Regular)',
                'codes': {
                    'BEN': 'AMALR',
                    'BC': 'AMALR',
                    'ULC': 'AMALR',
                    'CC': 'AMALR'
                },
            },
            'vertical': {
                'name': 'verticalAmalgamation',
                'title': 'Amalgamation Application Short-form (Vertical)',
                'codes': {
                    'BEN': 'AMALV',
                    'BC': 'AMALV',
                    'ULC': 'AMALV',
                    'CC': 'AMALV'
                },
            },
            'horizontal': {
                'name': 'horizontalAmalgamation',
                'title': 'Amalgamation Application Short-form (Horizontal)',
                'codes': {
                    'BEN': 'AMALH',
                    'BC': 'AMALH',
                    'ULC': 'AMALH',
                    'CC': 'AMALH'
                },
            }
        },
        'amalgamationOut': {
            'name': 'amalgamationOut',
            'title': 'Amalgamation Out',
            'codes': {
                'BC': 'AMALO',
                'BEN': 'AMALO',
                'ULC': 'AMALO',
                'CC': 'AMALO',
                'C': 'AMALO',
                'CBEN': 'AMALO',
                'CUL': 'AMALO',
                'CCC': 'AMALO'
            }
        },
        'annualReport': {
            'name': 'annualReport',
            'title': 'Annual Report Filing',
            'codes': {
                'CP': 'OTANN',
                'BEN': 'BCANN',
                'BC': 'BCANN',
                'ULC': 'BCANN',
                'CC': 'BCANN',
                'CBEN': 'BCANN',
                'C': 'BCANN',
                'CUL': 'BCANN',
                'CCC': 'BCANN'
            }
        },
        'appointReceiver': {
            'name': 'appointReceiver',
            'title': 'Appoint Receiver Filing',
            'codes': {
                'BEN': 'NOARM',
                'BC': 'NOARM',
                'ULC': 'NOARM',
                'CC': 'NOARM',
                'CBEN': 'NOARM',
                'C': 'NOARM',
                'CUL': 'NOARM',
                'CCC': 'NOARM'
            }
        },
        'ceaseReceiver': {
            'name': 'ceaseReceiver',
            'title': 'Cease Receiver Filing',
            'displayName': 'Cease Receiver',
            'codes': {
                'BEN': 'NOCER',
                'BC': 'NOCER',
                'ULC': 'NOCER',
                'CC': 'NOCER',
                'CBEN': 'NOCER',
                'C': 'NOCER',
                'CUL': 'NOCER',
                'CCC': 'NOCER'
            }
        },
        'changeOfAddress': {
            'name': 'changeOfAddress',
            'title': 'Change of Address Filing',
            'codes': {
                'CP': 'OTADD',
                'BEN': 'BCADD',
                'BC': 'BCADD',
                'ULC': 'BCADD',
                'CC': 'BCADD',
                'CBEN': 'BCADD',
                'C': 'BCADD',
                'CUL': 'BCADD',
                'CCC': 'BCADD'
            }
        },
        'changeOfDirectors': {
            'name': 'changeOfDirectors',
            'title': 'Change of Directors Filing',
            'codes': {
                'CP': 'OTCDR',
                'BEN': 'BCCDR',
                'BC': 'BCCDR',
                'ULC': 'BCCDR',
                'CC': 'BCCDR',
                'CBEN': 'BCCDR',
                'C': 'BCCDR',
                'CUL': 'BCCDR',
                'CCC': 'BCCDR'
            },
            'free': {
                'codes': {
                    'CP': 'OTFDR',
                    'BEN': 'BCFDR',
                    'BC': 'BCFDR',
                    'ULC': 'BCFDR',
                    'CC': 'BCFDR',
                    'CBEN': 'BCFDR',
                    'C': 'BCFDR',
                    'CUL': 'BCFDR',
                    'CCC': 'BCFDR'
                }
            }
        },
        'changeOfName': {
            'name': 'changeOfName',
            'title': 'Change of Name Filing',
            'codes': {
                'CP': 'OTCON',
            }
        },
        'changeOfRegistration': {
            'name': 'changeOfRegistration',
            'title': 'Change of Registration',
            'codes': {
                'SP': 'FMCHANGE',
                'GP': 'FMCHANGE'
            }
        },
        'consentAmalgamationOut': {
            'name': 'consentAmalgamationOut',
            'title': 'Consent Amalgamation Out',
            'codes': {
                'BC': 'IAMGO',
                'BEN': 'IAMGO',
                'ULC': 'IAMGO',
                'CC': 'IAMGO',
                'C': 'IAMGO',
                'CBEN': 'IAMGO',
                'CUL': 'IAMGO',
                'CCC': 'IAMGO'
            }
        },
        'consentContinuationOut': {
            'name': 'consentContinuationOut',
            'title': 'Consent Continuation Out',
            'codes': {
                'BC': 'CONTO',
                'BEN': 'CONTO',
                'ULC': 'CONTO',
                'CC': 'CONTO',
                'C': 'CONTO',
                'CBEN': 'CONTO',
                'CUL': 'CONTO',
                'CCC': 'CONTO'
            }
        },
        'continuationIn': {
            'name': 'continuationIn',
            'title': 'Continuation In',
            'temporaryCorpTypeCode': 'CTMP',
            'staffApprovalRequired': True,
            'codes': {
                'C': 'CONTI',
                'CBEN': 'CONTI',
                'CUL': 'CONTI',
                'CCC': 'CONTI'
            }
        },
        'continuationOut': {
            'name': 'continuationOut',
            'title': 'Continuation Out',
            'codes': {
                'BC': 'COUTI',
                'BEN': 'COUTI',
                'ULC': 'COUTI',
                'CC': 'COUTI',
                'C': 'COUTI',
                'CBEN': 'COUTI',
                'CUL': 'COUTI',
                'CCC': 'COUTI'
            }
        },
        'conversion': {
            'name': 'conversion',
            'title': 'Conversion Ledger',
            'codes': {
                'SP': 'FMCONV',
                'GP': 'FMCONV'
            },
        },
        'correction': {
            'name': 'correction',
            'title': 'Correction',
            'codes': {
                'BEN': 'CRCTN',
                'BC': 'CRCTN',
                'ULC': 'CRCTN',
                'CC': 'CRCTN',
                'CP': 'CRCTN',
                'SP': 'FMCORR',
                'GP': 'FMCORR',
                'CBEN': 'CRCTN',
                'C': 'CRCTN',
                'CUL': 'CRCTN',
                'CCC': 'CRCTN',
            }
        },
        'courtOrder': {
            'name': 'courtOrder',
            'title': 'Court Order',
            'displayName': 'Court Order',
            'codes': {
                'SP': 'COURT',
                'GP': 'COURT',
                'CP': 'COURT',
                'BC': 'COURT',
                'BEN': 'COURT',
                'CC': 'COURT',
                'ULC': 'COURT',
                'C': 'COURT',
                'CBEN': 'COURT',
                'CUL': 'COURT',
                'CCC': 'COURT',
            }
        },
        'dissolution': {
            'name': 'dissolution',
            'voluntary': {
                'name': 'voluntary',
                'title': 'Voluntary Dissolution',
                'codes': {
                    'CP': 'DIS_VOL',
                    'BC': 'DIS_VOL',
                    'BEN': 'DIS_VOL',
                    'ULC': 'DIS_VOL',
                    'CC': 'DIS_VOL',
                    'LLC': 'DIS_VOL',
                    'SP': 'DIS_VOL',
                    'GP': 'DIS_VOL',
                    'C': 'DIS_VOL',
                    'CBEN': 'DIS_VOL',
                    'CUL': 'DIS_VOL',
                    'CCC': 'DIS_VOL',
                }
            },
            'administrative': {
                'name': 'administrative',
                'title': 'Administrative Dissolution',
                'codes': {
                    'CP': 'DIS_ADM',
                    'BC': 'DIS_ADM',
                    'BEN': 'DIS_ADM',
                    'ULC': 'DIS_ADM',
                    'CC': 'DIS_ADM',
                    'LLC': 'DIS_ADM',
                    'SP': 'DIS_ADM',
                    'GP': 'DIS_ADM',
                    'C': 'DIS_ADM',
                    'CBEN': 'DIS_ADM',
                    'CUL': 'DIS_ADM',
                    'CCC': 'DIS_ADM',
                }
            }
        },
        'incorporationApplication': {
            'name': 'incorporationApplication',
            'title': 'Incorporation Application',
            'codes': {
                'BEN': 'BCINC',
                'BC': 'BCINC',
                'ULC': 'BCINC',
                'CC': 'BCINC',
                'CP': 'OTINC'
            },
            'temporaryCorpTypeCode': 'TMP'
        },
        'noticeOfWithdrawal': {
            'name': 'noticeOfWithdrawal',
            'title': 'Notice of Withdrawal',
            'displayName': 'Notice of Withdrawal',
            'codes': {
                'BC': 'NWITH',
                'BEN': 'NWITH',
                'ULC': 'NWITH',
                'CC': 'NWITH',
                'C': 'NWITH',
                'CBEN': 'NWITH',
                'CUL': 'NWITH',
                'CCC': 'NWITH'
            }
        },
        'registration': {
            'name': 'registration',
            'title': 'Registration',
            'codes': {
                'SP': 'FRREG',
                'GP': 'FRREG'
            },
            'temporaryCorpTypeCode': 'RTMP'
        },
        'restoration': {
            'name': 'restoration',
            'fullRestoration': {
                'name': 'fullRestoration',
                'title': 'Full Restoration',
                'codes': {
                    'BC': 'RESTF',
                    'BEN': 'RESTF',
                    'ULC': 'RESTF',
                    'CC': 'RESTF',
                    'C': 'RESTF',
                    'CBEN': 'RESTF',
                    'CUL': 'RESTF',
                    'CCC': 'RESTF'
                }
            },
            'limitedRestoration': {
                'name': 'limitedRestoration',
                'title': 'Limited Restoration',
                'codes': {
                    'BC': 'RESTL',
                    'BEN': 'RESTL',
                    'ULC': 'RESTL',
                    'CC': 'RESTL',
                    'C': 'RESTL',
                    'CBEN': 'RESTL',
                    'CUL': 'RESTL',
                    'CCC': 'RESTL'
                }
            },
            'limitedRestorationExtension': {
                'name': 'limitedRestorationExtension',
                'title': 'Limited Restoration Extension',
                'codes': {
                    'BC': 'RESXL',
                    'BEN': 'RESXL',
                    'ULC': 'RESXL',
                    'CC': 'RESXL',
                    'C': 'RESXL',
                    'CBEN': 'RESXL',
                    'CUL': 'RESXL',
                    'CCC': 'RESXL'
                }
            },
            'limitedRestorationToFull': {
                'name': 'limitedRestorationToFull',
                'title': 'Limited Restoration To Full',
                'codes': {
                    'BC': 'RESXF',
                    'BEN': 'RESXF',
                    'ULC': 'RESXF',
                    'CC': 'RESXF',
                    'C': 'RESXF',
                    'CBEN': 'RESXF',
                    'CUL': 'RESXF',
                    'CCC': 'RESXF'
                }
            }
        },
        'specialResolution': {
            'name': 'specialResolution',
            'title': 'Special Resolution',
            'codes': {
                'CP': 'SPRLN'
            }
        },
        'transition': {
            'name': 'transition',
            'title': 'Transition',
            'codes': {
                'BC': 'TRANS',
                'BEN': 'TRANS',
                'ULC': 'TRANS',
                'CC': 'TRANS',
                'C': 'TRANS',
                'CBEN': 'TRANS',
                'CUL': 'TRANS',
                'CCC': 'TRANS'
            }
        },
        'transparencyRegister': {
            'name': 'transparencyRegister',
            'annual': {
                'name': 'transparencyRegister',
                'title': 'Transparency Register - Annual Filing',
                'codes': {
                    'BC': 'REGSIGIN',
                    'BEN': 'REGSIGIN',
                    'ULC': 'REGSIGIN',
                    'CC': 'REGSIGIN',
                    'C': 'REGSIGIN',
                    'CBEN': 'REGSIGIN',
                    'CUL': 'REGSIGIN',
                    'CCC': 'REGSIGIN'
                }
            },
            'change': {
                'name': 'transparencyRegister',
                'title': 'Transparency Register Filing',
                'codes': {
                    'BC': 'REGSIGIN',
                    'BEN': 'REGSIGIN',
                    'ULC': 'REGSIGIN',
                    'CC': 'REGSIGIN',
                    'C': 'REGSIGIN',
                    'CBEN': 'REGSIGIN',
                    'CUL': 'REGSIGIN',
                    'CCC': 'REGSIGIN'
                }
            },
            'initial': {
                'name': 'transparencyRegister',
                'title': 'Transparency Register Filing',
                'codes': {
                    'BC': 'REGSIGIN',
                    'BEN': 'REGSIGIN',
                    'ULC': 'REGSIGIN',
                    'CC': 'REGSIGIN',
                    'C': 'REGSIGIN',
                    'CBEN': 'REGSIGIN',
                    'CUL': 'REGSIGIN',
                    'CCC': 'REGSIGIN'
                }
            }
        },

        # changing the structure of fee code in courtOrder/registrarsNotation/registrarsOrder
        # for all the business the fee code remain same as NOFEE (Staff)
        'adminFreeze': {'name': 'adminFreeze', 'title': 'Admin Freeze', 'code': 'NOFEE'},
        'putBackOff': {'name': 'putBackOff', 'title': 'Put Back Off', 'code': 'NOFEE'},
        'putBackOn': {'name': 'putBackOn', 'title': 'Put Back On', 'code': 'NOFEE'},
        'registrarsNotation': {'name': 'registrarsNotation', 'title': 'Registrars Notation', 'code': 'NOFEE'},
        'registrarsOrder': {'name': 'registrarsOrder', 'title': 'Registrars Order', 'code': 'NOFEE'}
    }

    FILING_SUB_TYPE_KEYS: Final = {
        # FUTURE: uncomment and update such that FEE codes can be defined like restoration sub-types.  Tests were
        #  breaking and more testing was req'd so did not make refactor when introducing this dictionary.
        'dissolution': 'dissolutionType',
        'restoration': 'type',
        'amalgamationApplication': 'type',
        'transparencyRegister': 'type'
    }

    __tablename__ = 'filings'
    # this mapper is used so that new and old versions of the service can be run simultaneously,
    # making rolling upgrades easier
    # This is used by SQLAlchemy to explicitly define which fields we're interested
    # so it doesn't freak out and say it can't map the structure if other fields are present.
    # This could occur from a failed deploy or during an upgrade.
    # The other option is to tell SQLAlchemy to ignore differences, but that is ambiguous
    # and can interfere with Alembic upgrades.
    #
    # NOTE: please keep mapper names in alpha-order, easier to track that way
    #       Exception, id is always first, _fields first
    __mapper_args__ = {
        'include_properties': [
            'id',
            '_completion_date',
            '_filing_date',
            '_filing_json',
            '_filing_type',
            '_filing_sub_type',
            '_meta_data',
            '_payment_completion_date',
            '_payment_status_code',
            '_payment_token',
            '_source',
            '_status',
            'business_id',
            'colin_only',
            'court_order_date',
            'court_order_effect_of_order',
            'court_order_file_number',
            'deletion_locked',
            'hide_in_ledger',
            'effective_date',
            'order_details',
            'paper_only',
            'parent_filing_id',
            'payment_account',
            'submitter_id',
            'submitter_roles',
            'tech_correction_json',
            'temp_reg',
            'transaction_id',
            'approval_type',
            'application_date',
            'notice_date',
            'withdrawal_pending',
            'withdrawn_filing_id'
        ]
    }

    id = db.Column(db.Integer, primary_key=True)
    _completion_date = db.Column('completion_date', db.DateTime(timezone=True))
    _filing_date = db.Column('filing_date', db.DateTime(timezone=True), default=datetime.utcnow)
    _filing_type = db.Column('filing_type', db.String(30))
    _filing_sub_type = db.Column('filing_sub_type', db.String(30))
    _filing_json = db.Column('filing_json', JSONB)
    _meta_data = db.Column('meta_data', JSONB)
    _payment_status_code = db.Column('payment_status_code', db.String(50))
    _payment_token = db.Column('payment_id', db.String(4096))
    _payment_completion_date = db.Column('payment_completion_date', db.DateTime(timezone=True))
    _status = db.Column('status', db.String(20), default=Status.DRAFT)
    _source = db.Column('source', db.String(15), default=Source.LEAR.value)
    paper_only = db.Column('paper_only', db.Boolean, unique=False, default=False)
    colin_only = db.Column('colin_only', db.Boolean, unique=False, default=False)
    payment_account = db.Column('payment_account', db.String(30))
    effective_date = db.Column('effective_date', db.DateTime(timezone=True), default=datetime.utcnow)
    submitter_roles = db.Column('submitter_roles', db.String(200))
    tech_correction_json = db.Column('tech_correction_json', JSONB)
    court_order_file_number = db.Column('court_order_file_number', db.String(20))
    court_order_date = db.Column('court_order_date', db.DateTime(timezone=True), default=None)
    court_order_effect_of_order = db.Column('court_order_effect_of_order', db.String(500))
    order_details = db.Column(db.String(2000))
    deletion_locked = db.Column('deletion_locked', db.Boolean, unique=False, default=False)
    approval_type = db.Column('approval_type', db.String(15))
    application_date = db.Column('application_date', db.DateTime(timezone=True))
    notice_date = db.Column('notice_date', db.DateTime(timezone=True))
    resubmission_date = db.Column('resubmission_date', db.DateTime(timezone=True))
    hide_in_ledger = db.Column('hide_in_ledger', db.Boolean, unique=False, default=False)
    withdrawal_pending = db.Column('withdrawal_pending', db.Boolean, unique=False, default=False)

    # # relationships
    transaction_id = db.Column('transaction_id', db.BigInteger,
                               db.ForeignKey('transaction.id'))
    business_id = db.Column('business_id', db.Integer,
                            db.ForeignKey('businesses.id'))
    temp_reg = db.Column('temp_reg', db.String(10),
                         db.ForeignKey('registration_bootstrap.identifier'))
    submitter_id = db.Column('submitter_id', db.Integer,
                             db.ForeignKey('users.id'))

    filing_submitter = db.relationship('User',
                                       backref=backref('filing_submitter', uselist=False),
                                       foreign_keys=[submitter_id])

    colin_event_ids = db.relationship('ColinEventId', lazy='select')

    comments = db.relationship('Comment', lazy='dynamic')
    documents = db.relationship('Document', lazy='dynamic')
    filing_party_roles = db.relationship('PartyRole', lazy='dynamic')
    review = db.relationship('Review', lazy='dynamic')

    parent_filing_id = db.Column(db.Integer, db.ForeignKey('filings.id'))
    parent_filing = db.relationship('Filing',
                                    remote_side=[id],
                                    backref=backref('children', uselist=True),
                                    foreign_keys=[parent_filing_id])

    withdrawn_filing_id = db.Column('withdrawn_filing_id', db.Integer,
                                    db.ForeignKey('filings.id'))
    withdrawn_filing = db.relationship('Filing',
                                       remote_side=[id],
                                       foreign_keys=[withdrawn_filing_id])

    # properties
    @property
    def completion_date(self):
        """Property containing the filing type."""
        return self._completion_date

    @hybrid_property
    def filing_date(self):
        """Property containing the date a filing was submitted."""
        return self._filing_date

    @filing_date.setter
    def filing_date(self, value: datetime):
        if self.locked:
            self._raise_default_lock_exception()
        self._filing_date = value

    @property
    def filing_type(self):
        """Property containing the filing type."""
        return self._filing_type

    @property
    def filing_sub_type(self):
        """Property containing the filing sub type."""
        return self._filing_sub_type

    @hybrid_property
    def payment_status_code(self):
        """Property containing the payment error type."""
        return self._payment_status_code

    @payment_status_code.setter
    def payment_status_code(self, error_type: str):
        if self.locked:
            self._raise_default_lock_exception()
        self._payment_status_code = error_type

    @hybrid_property
    def payment_token(self):
        """Property containing the payment token."""
        return self._payment_token

    @payment_token.setter
    def payment_token(self, token: int):
        if self.locked:
            self._raise_default_lock_exception()
        self._payment_token = token

    @hybrid_property
    def payment_completion_date(self):
        """Property containing the date the payment cleared."""
        return self._payment_completion_date

    @payment_completion_date.setter
    def payment_completion_date(self, value: datetime):

        if self.locked or \
                (self._payment_token and self._filing_json):
            self._payment_completion_date = value
            # if self.effective_date is None or \
            #         self.effective_date <= self._payment_completion_date:
            #     self._status = Filing.Status.COMPLETED.value
        else:
            raise BusinessException(
                error="Payment Dates cannot set for unlocked filings unless the filing hasn't been saved yet.",
                status_code=HTTPStatus.FORBIDDEN
            )

    @property
    def status(self):
        """Property containing the filing status."""
        # pylint: disable=W0212; prevent infinite loop
        if self._status == Filing.Status.COMPLETED \
            and self.parent_filing_id \
                and self.parent_filing._status == Filing.Status.COMPLETED:
            return Filing.Status.CORRECTED.value
        return self._status

    @hybrid_property
    def source(self):
        """Property containing the filing source."""
        return self._source

    @source.setter
    def source(self, source: str):
        """Property containing the filing source."""
        if source not in [x.value for x in self.Source]:
            raise BusinessException(
                error='Tried to update the filing with an invalid source.',
                status_code=HTTPStatus.BAD_REQUEST
            )
        self._source = source

    @hybrid_property
    def filing_json(self):
        """Property containing the filings data."""
        return self._filing_json

    @filing_json.setter
    def filing_json(self, json_data: dict):
        """Property containing the filings data."""
        if self.locked:
            self._raise_default_lock_exception()

        try:
            self._filing_type = json_data.get('filing', {}).get('header', {}).get('name')
            if not self._filing_type:
                raise Exception  # pylint: disable=broad-exception-raised
        except Exception as err:
            raise BusinessException(
                error='No filings found.',
                status_code=HTTPStatus.UNPROCESSABLE_ENTITY
            ) from err

        self._filing_sub_type = self.get_filings_sub_type(self._filing_type, json_data)

        if self._payment_token:
            valid, err = rsbc_schemas.validate(json_data, 'filing')
            if not valid:
                self._filing_type = None
                self._payment_token = None
                errors = build_schema_error_response(err)
                raise BusinessException(
                    error=f'{errors}',
                    status_code=HTTPStatus.UNPROCESSABLE_ENTITY
                )

            self._status = Filing.Status.PENDING.value
        self._filing_json = json_data

    @property
    def json_legal_type(self):
        """Return the legal type from a filing_json or None."""
        filing = self._filing_json.get('filing', {})
        legal_type = filing.get('business', {}).get('legalType', None)
        if legal_type is None:
            legal_type = filing.get(self.filing_type, {}).get('nameRequest').get('legalType', None)
        return legal_type

    @property
    def json_nr(self):
        """Return the NR Number from a filing_json or None."""
        return self._filing_json.get('filing', {})\
            .get(self.filing_type, {}).get('nameRequest', {}).get('nrNumber', None)

    @property
    def meta_data(self):
        """Return the meta data collected about a filing, stored as JSON."""
        return self._meta_data

    @property
    def locked(self):
        """Return the locked state of the filing.

        Once a filing, with valid json has an invoice attached, it can no longer be altered and is locked.
        Exception to this rule, payment_completion_date requires the filing to be locked.
        """
        if self.deletion_locked:
            return True

        insp = inspect(self)
        attr_state = insp.attrs._payment_token  # pylint: disable=protected-access;
        # inspect requires the member, and the hybrid decorator doesn't help us here
        if (self._payment_token and not attr_state.history.added) or self.colin_event_ids:
            return True

        return False

    def set_processed(self, business_type):
        """Assign the completion and effective dates, unless they are already set."""
        if not self._completion_date:
            self._completion_date = datetime.utcnow()
        if not self.effective_date_can_be_before_payment_completion_date(business_type) and (
                self.effective_date is None or (
                    self.payment_completion_date
                    and self.effective_date < self.payment_completion_date  # pylint: disable=comparison-with-callable
                )):
            self.effective_date = self.payment_completion_date

    def effective_date_can_be_before_payment_completion_date(self, business_type):
        """For AR or COD filings then the effective date can be before the payment date."""
        return self.filing_type in (Filing.FILINGS['annualReport'].get('name'),
                                    Filing.FILINGS['changeOfDirectors'].get('name'),
                                    Filing.FILINGS['transparencyRegister'].get('name'))

    @staticmethod
    def _raise_default_lock_exception():
        raise BusinessException(
            error='Filings cannot be changed after the invoice is created.',
            status_code=HTTPStatus.FORBIDDEN
        )

    @property
    def is_future_effective(self) -> bool:
        """Return True if the effective date is in the future."""
        with suppress(AttributeError, TypeError):
            if self.effective_date > self.payment_completion_date:
                return True
        return False

    @property
    def is_corrected(self):
        """Has this filing been corrected."""
        if (
                self.parent_filing and
                self.parent_filing.filing_type == Filing.FILINGS['correction'].get('name') and
                self.parent_filing.status == Filing.Status.COMPLETED.value
        ):
            return True
        return False

    @property
    def is_correction_pending(self):
        """Is there a pending correction for this filing."""
        if (
                self.parent_filing and
                self.parent_filing.filing_type == Filing.FILINGS['correction'].get('name') and
                self.parent_filing.status == Filing.Status.PENDING_CORRECTION.value
        ):
            return True
        return False

    @property
    def is_amalgamation_application(self):
        """Is this an amalgamation application filing."""
        return self.filing_type == Filing.FILINGS['amalgamationApplication'].get('name')

    @hybrid_property
    def comments_count(self):
        """Return the number of commentson this filing."""
        return self.comments.count()

    @comments_count.expression
    def comments_count(self):
        """Return comments count expression for this filing."""
        return (select([func.count(Comment.business_id)]).
                where(Comment.business_id == self.id).
                label('comments_count')
                )

    # json serializer
    @property
    def json(self):
        """Return a json representation of this object."""
        try:
            json_submission = copy.deepcopy(self.filing_json)
            json_submission['filing']['header']['date'] = self._filing_date.isoformat()
            json_submission['filing']['header']['filingId'] = self.id
            json_submission['filing']['header']['name'] = self.filing_type
            json_submission['filing']['header']['status'] = self.status
            json_submission['filing']['header']['availableOnPaperOnly'] = self.paper_only
            json_submission['filing']['header']['inColinOnly'] = self.colin_only
            json_submission['filing']['header']['deletionLocked'] = self.deletion_locked

            if self.effective_date:  # pylint: disable=using-constant-test
                json_submission['filing']['header']['effectiveDate'] = self.effective_date.isoformat()  # noqa: E501 pylint: disable=no-member, line-too-long
            if self._payment_status_code:
                json_submission['filing']['header']['paymentStatusCode'] = self.payment_status_code
            if self._payment_token:
                json_submission['filing']['header']['paymentToken'] = self.payment_token
            if self.submitter_id:
                json_submission['filing']['header']['submitter'] = self.filing_submitter.username
            if self.payment_account:
                json_submission['filing']['header']['paymentAccount'] = self.payment_account

            # add colin_event_ids
            json_submission['filing']['header']['colinIds'] = ColinEventId.get_by_filing_id(self.id)

            # add comments
            json_submission['filing']['header']['comments'] = [comment.json for comment in self.comments]

            # add affected filings list
            json_submission['filing']['header']['affectedFilings'] = [filing.id for filing in self.children]

            # add corrected flags
            json_submission['filing']['header']['isCorrected'] = self.is_corrected
            json_submission['filing']['header']['isCorrectionPending'] = self.is_correction_pending

            return json_submission
        except Exception as err:  # noqa: B901, E722
            raise KeyError from err

    @classmethod
    def find_by_id(cls, filing_id: str = None):
        """Return a Filing by the id."""
        filing = None
        if filing_id:
            filing = cls.query.filter_by(id=filing_id).one_or_none()
        return filing

    @staticmethod
    def get_temp_reg_filing(temp_reg_id: str, filing_id: str = None):
        """Return a filing by the temp id and filing id (if applicable)."""
        if not filing_id:
            return db.session.query(Filing).filter(Filing.temp_reg == temp_reg_id).one_or_none()

        return (
            db.session.query(Filing).filter(
                db.or_(
                    db.and_(
                        Filing.id == filing_id,
                        Filing.temp_reg == temp_reg_id
                    ),
                    db.and_(  # special case for NoW
                        Filing.id == filing_id,
                        Filing._filing_type == 'noticeOfWithdrawal',
                        Filing.withdrawn_filing_id == db.session.query(Filing.id)
                        .filter(Filing.temp_reg == temp_reg_id)
                        .scalar_subquery()
                    )
                )
            ).one_or_none())

    @staticmethod
    def get_temp_reg_filing_by_withdrawn_filing(filing_id: str, withdrawn_filing_id: str, filing_type: str = None):
        """Return an temp reg Filing by withdrawn filing."""
        q = db.session.query(Filing). \
            filter(Filing.withdrawn_filing_id == withdrawn_filing_id). \
            filter(Filing.id == filing_id)

        if filing_type:
            q = q.filter(Filing._filing_type == filing_type)

        filing = q.one_or_none()
        return filing

    @staticmethod
    def get_filing_by_payment_token(token: str):
        """Return a Filing by it's payment token."""
        filing = db.session.query(Filing). \
            filter(Filing.payment_token == token). \
            one_or_none()
        return filing

    @staticmethod
    def get_filings_by_status(business_id: int, status: list, after_date: date = None):
        """Return the filings with statuses in the status array input."""
        query = db.session.query(Filing). \
            filter(Filing.business_id == business_id). \
            filter(Filing._status.in_(status)). \
            order_by(Filing._filing_date.desc(), Filing.effective_date.desc())  # pylint: disable=no-member;
        # member provided via SQLAlchemy

        if after_date:
            query = query.filter(Filing._filing_date >= after_date)

        return query.all()

    @staticmethod
    def get_incomplete_filings_by_type(business_id: int, filing_type: str):
        """Return the incomplete filings of a particular type."""
        filings = db.session.query(Filing). \
            filter(Filing.business_id == business_id). \
            filter(Filing._filing_type == filing_type). \
            filter(not_(Filing._status.in_([Filing.Status.COMPLETED.value, Filing.Status.WITHDRAWN.value]))). \
            order_by(desc(Filing.filing_date)). \
            all()
        return filings

    @staticmethod
    def get_filings_by_types(business_id: int, filing_types):
        """Return the completed filings of a particular type."""
        filings = db.session.query(Filing). \
            filter(Filing.business_id == business_id). \
            filter(Filing._filing_type.in_(filing_types)). \
            filter(Filing._status == Filing.Status.COMPLETED.value). \
            order_by(desc(Filing.transaction_id)). \
            all()
        return filings

    @staticmethod
    def get_conversion_filings_by_conv_types(business_id: int, filing_types: list):
        """Return the conversion filings of a particular conv type.

        Records only exist in some legacy corps imported from COLIN.
        """
        filings = db.session.query(Filing). \
            filter(Filing.business_id == business_id). \
            filter(Filing._filing_type == 'conversion'). \
            filter(
                Filing._meta_data.op('->')('conversion').op('->>')('convFilingType').in_(filing_types)
            ). \
            order_by(desc(Filing.transaction_id)). \
            all()

        return filings

    @staticmethod
    def get_incomplete_filings_by_types(business_id: int, filing_types: list, excluded_statuses: list = None):
        """Return the filings of particular types and statuses.

        excluded_statuses is a list of filing statuses that will be excluded from the query for incomplete filings
        """
        excluded_statuses = [] if excluded_statuses is None else excluded_statuses

        filings = db.session.query(Filing). \
            filter(Filing.business_id == business_id). \
            filter(Filing._filing_type.in_(filing_types)). \
            filter(not_(Filing._status.in_([Filing.Status.COMPLETED.value, Filing.Status.WITHDRAWN.value]))). \
            filter(not_(Filing._status.in_(excluded_statuses))). \
            order_by(desc(Filing.effective_date)). \
            all()
        return filings

    @staticmethod
    def get_filings_by_type_pairs(business_id: int, filing_type_pairs: list, status: list, return_unique_pairs=False):
        """Return the filings of particular filing type/sub-type pairs as well as statuses.

        If return_unique_pairs is True, only return one instance of each filing type/sub-type pair.
        """
        filing_type_conditions = [and_(Filing._filing_type == filing_type,
                                       Filing._filing_sub_type == filing_sub_type).self_group()
                                  for filing_type, filing_sub_type in filing_type_pairs]

        base_query = db.session.query(Filing). \
            filter(Filing.business_id == business_id). \
            filter(Filing._status.in_(status)). \
            filter(or_(*filing_type_conditions))

        # pylint: disable=W0212; prevent infinite loop
        if return_unique_pairs:
            subquery = (
                base_query.with_entities(
                    Filing._filing_type,
                    Filing._filing_sub_type,
                    func.max(Filing.id).label('id')
                )
                .group_by(Filing._filing_type, Filing._filing_sub_type)
                .subquery()
            )
            query = (
                base_query.join(
                    subquery,
                    and_(Filing.id == subquery.c.id)
                )
            )
        else:
            query = base_query

        filings = query.all()
        return filings

    @staticmethod
    def get_most_recent_filing(business_id: str, filing_type: str = None, filing_sub_type: str = None):
        """Return the most recent filing.

        filing_type is required, if filing_sub_type is provided, it will be used to filter the query.
        """
        query = db.session.query(Filing). \
            filter(Filing.business_id == business_id). \
            filter(Filing._status == Filing.Status.COMPLETED.value)
        if filing_type:
            query = query.filter(Filing._filing_type == filing_type)
            if filing_sub_type:
                query = query.filter(Filing._filing_sub_type == filing_sub_type)

        query = query.order_by(Filing.transaction_id.desc())
        return query.first()

    @staticmethod
    def get_most_recent_legal_filing(business_id: str, filing_type: str = None):
        """Return the most recent filing containing the legal_filing type."""
        query = db.session.query(db.func.max(Filing._filing_date).label('last_filing_date')).\
            filter(Filing.business_id == business_id).\
            filter(Filing._status == Filing.Status.COMPLETED.value)
        if filing_type:
            expr = Filing._filing_json[('filing', filing_type)]
            query = query.filter(or_(Filing._filing_type == filing_type,
                                     expr.label('legal_filing_type').isnot(None)))
        max_filing = query.subquery()

        filing = Filing.query.join(max_filing, Filing._filing_date == max_filing.c.last_filing_date). \
            filter(Filing.business_id == business_id). \
            filter(Filing._status == Filing.Status.COMPLETED.value). \
            order_by(Filing.id.desc())

        # As the JSON query is new for most, leaving the debug stmnt
        # that dumps the query for easier debugging.
        # current_app.logger.debug(
        #     str(filing.statement.compile(
        #         dialect=dialect(),
        #         compile_kwargs={'literal_binds': True}))
        # )

        return filing.first()

    @staticmethod
    def get_completed_filings_for_colin(limit=20, offset=0):
        """Return the filings based on limit and offset."""
        from .business import Business  # noqa: F401; pylint: disable=import-outside-toplevel
        excluded_filings = [
            'lear_epoch',
            'adminFreeze',
            'courtOrder',
            'registrarsNotation',
            'registrarsOrder',
            'transparencyRegister'
        ]
        excluded_businesses = [Business.LegalTypes.SOLE_PROP.value, Business.LegalTypes.PARTNERSHIP.value]
        filings = db.session.query(Filing).join(Business). \
            filter(
                ~Business.legal_type.in_(excluded_businesses),
                ~Filing._filing_type.in_(excluded_filings),
                Filing.colin_event_ids == None,  # pylint: disable=singleton-comparison # noqa: E711;
                Filing._status == Filing.Status.COMPLETED.value,
                Filing._source == Filing.Source.LEAR.value,
                Filing.effective_date != None   # pylint: disable=singleton-comparison # noqa: E711;
            ).order_by(Filing.transaction_id).limit(limit).offset(offset).all()

        return filings

    @staticmethod
    def get_future_effective_filing_ids() -> List[int]:
        """Return filing ids which should be effective now."""
        filings = db.session.query(Filing.id). \
            filter(Filing._status == Filing.Status.PAID.value). \
            filter(Filing.effective_date <= datetime.now(timezone.utc)).all()
        return [filing.id for filing in filings]

    @staticmethod
    def get_all_filings_by_status(status):
        """Return all filings based on status."""
        filings = db.session.query(Filing). \
            filter(Filing._status == status).all()  # pylint: disable=singleton-comparison # noqa: E711;
        return filings

    @staticmethod
    def get_previous_completed_filing(filing):
        """Return the previous completed filing."""
        query = db.session.query(Filing). \
            filter(Filing.business_id == filing.business_id). \
            filter(Filing._status == Filing.Status.COMPLETED.value)

        if filing.transaction_id:  # transaction_id will be None for the pending filings (intermediate state)
            query = query.filter(Filing.transaction_id < filing.transaction_id)

        return query.order_by(Filing.transaction_id.desc()).first()

    @staticmethod
    def has_completed_filing(business_id: int, filing_type: str) -> bool:
        """Return whether a completed filing of a given filing type exists."""
        query = db.session.query(Filing). \
            filter(Filing.business_id == business_id). \
            filter(Filing._filing_type == filing_type). \
            filter(Filing._status == Filing.Status.COMPLETED.value)
        exists_stmt = query.exists()
        filing_exists = db.session.query(exists_stmt).scalar()
        return filing_exists

    @staticmethod
    def get_filings_sub_type(filing_type: str, filing_json: dict):
        """Return sub-type from filing json if sub-type exists for filing type."""
        filing_sub_type_key = Filing.FILING_SUB_TYPE_KEYS.get(filing_type)
        if filing_sub_type_key:
            filing_sub_type = filing_json['filing'][filing_type][filing_sub_type_key]
            return filing_sub_type

        return None

    @staticmethod
    def get_fee_code(legal_type: str, filing_type: str, filing_sub_type: str = None):
        """Return fee code for filing."""
        filing_dict = Filing.FILINGS.get(filing_type, None)

        if filing_sub_type:
            fee_code = filing_dict[filing_sub_type]['codes'].get(legal_type, None)
        else:
            if fee_code := filing_dict.get('code', None):
                return fee_code
            fee_code = filing_dict['codes'].get(legal_type, None)

        return fee_code

    def save(self):
        """Save and commit immediately."""
        db.session.add(self)
        db.session.commit()

    def save_to_session(self):
        """Save toThe session, do not commit immediately."""
        db.session.add(self)

    def delete(self):
        """Raise an error if the filing is locked."""
        if self.locked:
            raise BusinessException(
                error='Deletion not allowed.',
                status_code=HTTPStatus.FORBIDDEN
            )
        db.session.delete(self)
        db.session.commit()

    def reset_filing_to_draft(self):
        """Reset Filing to draft and remove payment token."""
        self._status = (Filing.Status.APPROVED.value
                        if self.FILINGS[self._filing_type].get('staffApprovalRequired', False)
                        else Filing.Status.DRAFT.value)
        self._payment_token = None
        self.save()

    def set_review_decision(self, filing_status):
        """Set review decision."""
        if filing_status not in [Filing.Status.CHANGE_REQUESTED.value,
                                 Filing.Status.APPROVED.value,
                                 Filing.Status.REJECTED.value]:
            raise BusinessException(
                error=f'Cannot set this filing status {filing_status}.',
                status_code=HTTPStatus.FORBIDDEN
            )
        self._status = filing_status
        self.save()

    def submit_filing_to_awaiting_review(self, submission_date):
        """Submit filing to awaiting review."""
        if self._status not in [Filing.Status.DRAFT.value,
                                Filing.Status.CHANGE_REQUESTED.value]:
            raise BusinessException(
                error='Cannot submit this filing to awaiting review status.',
                status_code=HTTPStatus.FORBIDDEN
            )
        self._status = Filing.Status.AWAITING_REVIEW.value
        self.resubmission_date = submission_date
        self.save()

    def legal_filings(self) -> List:
        """Return a list of the filings extracted from this filing submission.

        Returns: {
            List: or None of the Legal Filing JSON segments.
            }
        """
        if not self.filing_json:
            return None

        legal_filings = []
        filing = self.filing_json
        for k in filing['filing'].keys():  # pylint: disable=unsubscriptable-object
            if Filing.FILINGS.get(k, None):
                legal_filings.append(
                    {k: copy.deepcopy(filing['filing'].get(k))})  # pylint: disable=unsubscriptable-object

        return legal_filings


@event.listens_for(Filing, 'before_delete')
def block_filing_delete_listener_function(mapper, connection, target):  # pylint: disable=unused-argument
    """Raise an error when a delete is attempted on a Filing."""
    filing = target

    if filing.locked or filing.deletion_locked:
        raise BusinessException(
            error='Deletion not allowed.',
            status_code=HTTPStatus.FORBIDDEN
        )


@event.listens_for(Filing, 'before_insert')
@event.listens_for(Filing, 'before_update')
def receive_before_change(mapper, connection, target):  # pylint: disable=unused-argument; SQLAlchemy callback signature
    """Set the state of the filing, based upon column values."""
    filing = target

    # pylint: disable=protected-access
    if (filing._status in [Filing.Status.AWAITING_REVIEW.value,
                           Filing.Status.CHANGE_REQUESTED.value,
                           Filing.Status.REJECTED.value,
                           Filing.Status.WITHDRAWN.value] or
            (filing._status == Filing.Status.APPROVED.value and not filing.payment_token)):
        return  # should not override status in the review process

    # skip this status updater if the flag is set
    # Scenario: if this is a correction filing, and would have been set to COMPLETE by the entity filer, leave it as is
    # because it's been set to PENDING_CORRECTION by the entity filer.
    if hasattr(filing, 'skip_status_listener') and filing.skip_status_listener:
        return
    # changes are part of the class and are not externalized
    if filing.filing_type == 'lear_epoch':
        filing._status = Filing.Status.EPOCH.value  # pylint: disable=protected-access
    elif filing.transaction_id:
        filing._status = Filing.Status.COMPLETED.value  # pylint: disable=protected-access
    elif filing.payment_completion_date or filing.source == Filing.Source.COLIN.value:
        filing._status = Filing.Status.PAID.value  # pylint: disable=protected-access
    elif filing.payment_token:
        filing._status = Filing.Status.PENDING.value  # pylint: disable=protected-access
    else:
        filing._status = Filing.Status.DRAFT.value  # pylint: disable=protected-access
