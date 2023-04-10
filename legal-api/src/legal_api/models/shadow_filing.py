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
# limitations under the License
"""Filings are legal documents that alter the state of a business."""
import copy
from datetime import date, datetime
from enum import Enum
from http import HTTPStatus
from typing import Final, List

from legal_api.exceptions import BusinessException
from legal_api.models.legacy_outputs import LegacyOutputs
from sqlalchemy import desc, or_
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.ext.hybrid import hybrid_property

from .db import db  # noqa: I001
from .comment import Comment  # noqa: I001,F401,I003 pylint: disable=unused-import; needed by SQLAlchemy relationship


class ShadowFiling(db.Model):  # pylint: disable=too-many-instance-attributes,too-many-public-methods
    # allowing the model to be deep.
    """a shadow of the current filing record that stores basic filing data.

    Has new associations to legacy outputs from COLIN.
    """

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

    class Source(Enum):
        """Render an Enum of the Filing Sources."""

        COLIN = 'COLIN'
        LEAR = 'LEAR'

    # TODO: get legal types from defined class once table is made (getting it from Business causes circ import)
    FILINGS = {
        'affidavit': {
            'name': 'affidavit',
            'title': 'Affidavit',
            'codes': {
                'CP': 'AFDVT'
            }
        },
        'alteration': {
            'name': 'alteration',
            'title': 'Notice of Alteration Filing',
            'codes': {
                'BC': 'ALTER',
                'BEN': 'ALTER',
                'ULC': 'ALTER',
                'CC': 'ALTER'
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
                'CC': 'BCANN'
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
                'CC': 'BCADD'
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
                'CC': 'BCCDR'
            },
            'free': {
                'codes': {
                    'CP': 'OTFDR',
                    'BEN': 'BCFDR',
                    'BC': 'BCFDR',
                    'ULC': 'BCFDR',
                    'CC': 'BCFDR'
                }
            }
        },
        'changeOfName': {'name': 'changeOfName', 'title': 'Change of Name Filing'},
        'changeOfRegistration': {
            'name': 'changeOfRegistration',
            'title': 'Change of Registration',
            'codes': {
                'SP': 'FMCHANGE',
                'GP': 'FMCHANGE'
            }
        },
        'consentContinuationOut': {
            'name': 'consentContinuationOut',
            'title': 'Consent Continuation Out',
            'codes': {
                'BC': 'CONTO',
                'BEN': 'CONTO',
                'ULC': 'CONTO',
                'CC': 'CONTO'
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
                'GP': 'FMCORR'
            }
        },
        'dissolution': {
            'name': 'dissolution',
            'title': 'Voluntary dissolution',
            'codes': {
                'CP': 'DIS_VOL',
                'BC': 'DIS_VOL',
                'BEN': 'DIS_VOL',
                'ULC': 'DIS_VOL',
                'CC': 'DIS_VOL',
                'LLC': 'DIS_VOL',
                'SP': 'DIS_VOL',
                'GP': 'DIS_VOL'
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
                    'CC': 'RESTF'
                }
            },
            'limitedRestoration': {
                'name': 'limitedRestoration',
                'title': 'Limited Restoration',
                'codes': {
                    'BC': 'RESTL',
                    'BEN': 'RESTL',
                    'ULC': 'RESTL',
                    'CC': 'RESTL'
                }
            },
            'limitedRestorationExtension': {
                'name': 'limitedRestorationExtension',
                'title': 'Limited Restoration Extension',
                'codes': {
                    'BC': 'RESXL',
                    'BEN': 'RESXL',
                    'ULC': 'RESXL',
                    'CC': 'RESXL'
                }
            },
            'limitedRestorationToFull': {
                'name': 'limitedRestorationToFull',
                'title': 'Limited Restoration To Full',
                'codes': {
                    'BC': 'RESXF',
                    'BEN': 'RESXF',
                    'ULC': 'RESXF',
                    'CC': 'RESXF'
                }
            }
        },
        'specialResolution': {'name': 'specialResolution', 'title': 'Special Resolution',
                              'codes': {
                                  'CP': 'SPRLN'}},
        'transition': {
            'name': 'transition',
            'title': 'Transition',
            'codes': {
                'BC': 'TRANS',
                'BEN': 'TRANS',
                'ULC': 'TRANS',
                'CC': 'TRANS'
            }
        },

        # changing the structure of fee code in courtOrder/registrarsNotation/registrarsOrder
        # for all the business the fee code remain same as NOFEE (Staff)
        'adminFreeze': {'name': 'adminFreeze', 'title': 'Admin Freeze', 'code': 'NOFEE'},
        'courtOrder': {'name': 'courtOrder', 'title': 'Court Order', 'code': 'NOFEE'},
        'putBackOn': {'name': 'putBackOn', 'title': 'Put Back On', 'code': 'NOFEE'},
        'registrarsNotation': {'name': 'registrarsNotation', 'title': 'Registrars Notation', 'code': 'NOFEE'},
        'registrarsOrder': {'name': 'registrarsOrder', 'title': 'Registrars Order', 'code': 'NOFEE'}
    }

    FILING_SUB_TYPE_KEYS: Final = {
        # FUTURE: uncomment and update such that FEE codes can be defined like restoration sub-types.  Tests were
        #  breaking and more testing was req'd so did not make refactor when introducing this dictionary.
        # 'dissolution': 'dissolutionType',
        'restoration': 'type'
    }

    __tablename__ = 'shadow_filings'
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
            '_filing_date',
            '_filing_json',
            '_filing_type',
            '_filing_sub_type',
            '_meta_data',
            '_source',
            'business_id',
            'colin_only',
            'effective_date',
            'paper_only',
        ]
    }

    id = db.Column(db.Integer, primary_key=True)
    _filing_date = db.Column('filing_date', db.DateTime(timezone=True), default=datetime.utcnow)
    _filing_type = db.Column('filing_type', db.String(30))
    _filing_sub_type = db.Column('filing_sub_type', db.String(30))
    _filing_json = db.Column('filing_json', JSONB)
    _meta_data = db.Column('meta_data', JSONB)
    _status = db.Column('status', db.String(20), default=Status.DRAFT)
    _source = db.Column('source', db.String(15), default=Source.LEAR.value)
    effective_date = db.Column('effective_date', db.DateTime(timezone=True), default=datetime.utcnow)
    has_legacy_outputs = db.Column('has_legacy_outputs', db.Boolean, unique=False, default=False)
    colin_event_id = db.Column('colin_event_id', db.Integer, db.ForeignKey('legacy_outputs.colin_event_id'))
    locked = db.Column('locked', db.Boolean)

    # relationships
    business_id = db.Column('business_id', db.Integer,
                            db.ForeignKey('shadow_businesses.id'))

    # properties
    @hybrid_property
    def filing_date(self):
        """Property containing the date a filing was submitted."""
        return self._filing_date

    @property
    def filing_type(self):
        """Property containing the filing type."""
        return self._filing_type

    @property
    def filing_sub_type(self):
        """Property containing the filing sub type."""
        return self._filing_sub_type

    @property
    def status(self):
        """Property containing the filing status."""
        # pylint: disable=W0212; prevent infinite loop
        if self._status == ShadowFiling.Status.COMPLETED:
            return ShadowFiling.Status.CORRECTED.value
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
        self._filing_json = json_data

    @property
    def json_legal_type(self):
        """Return the legal type from a filing_json or None."""
        return self._filing_json.get('filing', {}).get('business', {}).get('legalType', None)

    @property
    def meta_data(self):
        """Return the meta data collected about a filing, stored as JSON."""
        return self._meta_data

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

            if self.effective_date:  # pylint: disable=using-constant-test
                json_submission['filing']['header']['effectiveDate'] = self.effective_date.isoformat()  # noqa: E501 pylint: disable=no-member, line-too-long

            # add colin_event_ids
            json_submission['filing']['header']['colinIds'] = LegacyOutputs.get_by_filing_id(self.id)

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
    def get_filings_by_status(business_id: int, status: list, after_date: date = None):
        """Return the filings with statuses in the status array input."""
        query = db.session.query(ShadowFiling). \
            filter(ShadowFiling.business_id == business_id). \
            filter(ShadowFiling._status.in_(status)). \
            order_by(ShadowFiling._filing_date.desc(), ShadowFiling.effective_date.desc())  # pylint: disable=no-member;
        # member provided via SQLAlchemy

        if after_date:
            query = query.filter(ShadowFiling._filing_date >= after_date)

        return query.all()

    @staticmethod
    def get_filings_by_type(business_id: int, filing_type: str):
        """Return the filings of a particular type."""
        filings = db.session.query(ShadowFiling). \
            filter(ShadowFiling.business_id == business_id). \
            filter(ShadowFiling._filing_type == filing_type). \
            filter(ShadowFiling._status != ShadowFiling.Status.COMPLETED.value). \
            order_by(desc(ShadowFiling.filing_date)). \
            all()
        return filings

    @staticmethod
    def get_filings_by_types(business_id: int, filing_types):
        """Return the filings of a particular type."""
        filings = db.session.query(ShadowFiling). \
            filter(ShadowFiling.business_id == business_id). \
            filter(ShadowFiling._filing_type.in_(filing_types)). \
            filter(ShadowFiling._status == ShadowFiling.Status.COMPLETED.value). \
            order_by(desc(ShadowFiling.effective_date)). \
            all()
        return filings

    @staticmethod
    def get_incomplete_filings_by_types(business_id: int, filing_types: list):
        """Return the filings of particular types and statuses."""
        filings = db.session.query(ShadowFiling). \
            filter(ShadowFiling.business_id == business_id). \
            filter(ShadowFiling._filing_type.in_(filing_types)). \
            filter(ShadowFiling._status != ShadowFiling.Status.COMPLETED.value). \
            order_by(desc(ShadowFiling.effective_date)). \
            all()
        return filings

    @staticmethod
    def get_a_businesses_most_recent_filing_of_a_type(business_id: int, filing_type: str):
        """Return the filings of a particular type."""
        max_filing = db.session.query(db.func.max(ShadowFiling._filing_date).label('last_filing_date')).\
            filter(ShadowFiling._filing_type == filing_type). \
            filter(ShadowFiling.business_id == business_id). \
            subquery()

        filing = ShadowFiling.query.join(max_filing, ShadowFiling._filing_date == max_filing.c.last_filing_date). \
            filter(ShadowFiling.business_id == business_id). \
            filter(ShadowFiling._filing_type == filing_type). \
            filter(ShadowFiling._status == ShadowFiling.Status.COMPLETED.value)

        return filing.one_or_none()

    @staticmethod
    def get_most_recent_legal_filing(business_id: str, filing_type: str = None):
        """Return the most recent filing containing the legal_filing type."""
        query = db.session.query(db.func.max(ShadowFiling._filing_date).label('last_filing_date')).\
            filter(ShadowFiling.business_id == business_id).\
            filter(ShadowFiling._status == ShadowFiling.Status.COMPLETED.value)
        if filing_type:
            expr = ShadowFiling._filing_json[('filing', filing_type)]
            query = query.filter(or_(ShadowFiling._filing_type == filing_type,
                                     expr.label('legal_filing_type').isnot(None)))
        max_filing = query.subquery()

        filing = ShadowFiling.query.join(max_filing, ShadowFiling._filing_date == max_filing.c.last_filing_date). \
            filter(ShadowFiling.business_id == business_id). \
            filter(ShadowFiling._status == ShadowFiling.Status.COMPLETED.value). \
            order_by(ShadowFiling.id.desc())

        # As the JSON query is new for most, leaving the debug stmnt
        # that dumps the query for easier debugging.
        # current_app.logger.debug(
        #     str(filing.statement.compile(
        #         dialect=dialect(),
        #         compile_kwargs={'literal_binds': True}))
        # )

        return filing.first()

    @staticmethod
    def get_completed_filings_for_colin():
        """Return the filings with statuses in the status array input."""
        from .shadow_business import ShadowBusiness   # noqa: F401; pylint: disable=import-outside-toplevel
        filings = db.session.query(ShadowFiling).join(ShadowBusiness). \
            filter(
                ~ShadowBusiness.legal_type.in_([
                    ShadowBusiness.LegalTypes.SOLE_PROP.value,
                    ShadowBusiness.LegalTypes.PARTNERSHIP.value]),
                ShadowFiling.colin_event_id == None,  # pylint: disable=singleton-comparison # noqa: E711;
                ShadowFiling._status == ShadowFiling.Status.COMPLETED.value,
                ShadowFiling.effective_date != None   # pylint: disable=singleton-comparison # noqa: E711;
            ).order_by(ShadowFiling.filing_date).all()
        return filings

    @staticmethod
    def get_all_filings_by_status(status):
        """Return all filings based on status."""
        filings = db.session.query(ShadowFiling). \
            filter(ShadowFiling._status == status).all()  # pylint: disable=singleton-comparison # noqa: E711;
        return filings

    @staticmethod
    def get_previous_completed_filing(filing):
        """Return the previous completed filing."""
        filings = db.session.query(ShadowFiling). \
            filter(ShadowFiling.business_id == filing.business_id). \
            filter(ShadowFiling._status == ShadowFiling.Status.COMPLETED.value). \
            filter(ShadowFiling.id < filing.id). \
            filter(ShadowFiling.effective_date < filing.effective_date). \
            order_by(ShadowFiling.effective_date.desc()).all()
        if filings:
            return filings[0]
        return None

    @staticmethod
    def get_filings_sub_type(filing_type: str, filing_json: dict):
        """Return sub-type from filing json if sub-type exists for filing type."""
        filing_sub_type_key = ShadowFiling.FILING_SUB_TYPE_KEYS.get(filing_type)
        if filing_sub_type_key:
            filing_sub_type = filing_json['filing'][filing_type][filing_sub_type_key]
            return filing_sub_type

        return None

    @staticmethod
    def get_fee_code(legal_type: str, filing_type: str, filing_sub_type: str = None):
        """Return fee code for filing."""
        filing_dict = ShadowFiling.FILINGS.get(filing_type, None)

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
            if ShadowFiling.FILINGS.get(k, None):
                legal_filings.append(
                    {k: copy.deepcopy(filing['filing'].get(k))})  # pylint: disable=unsubscriptable-object

        return legal_filings
