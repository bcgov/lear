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
"""Filings are legal documents that alter the state of a LegalEntity."""
import copy
from datetime import date, datetime
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

from .comment import Comment  # noqa: I001,F401,I003 pylint: disable=unused-import; needed by SQLAlchemy relationship
from .db import db  # noqa: I001


class DissolutionTypes(str, Enum):  # pylint: disable=too-many-lines
    """Dissolution types."""

    ADMINISTRATIVE = "administrative"
    COURT_ORDERED_LIQUIDATION = "courtOrderedLiquidation"
    INVOLUNTARY = "involuntary"
    VOLUNTARY = "voluntary"
    VOLUNTARY_LIQUIDATION = "voluntaryLiquidation"


# pylint: disable=too-many-instance-attributes,too-many-public-methods,protected-access
class Filing(db.Model):
    # allowing the model to be deep.
    """Immutable filing record.

    Manages the filing ledger for the associated LegalEntity.
    """

    class Status(str, Enum):
        """Render an Enum of the Filing Statuses."""

        COMPLETED = "COMPLETED"
        CORRECTED = "CORRECTED"
        DRAFT = "DRAFT"
        EPOCH = "EPOCH"
        ERROR = "ERROR"
        PAID = "PAID"
        PENDING = "PENDING"
        PENDING_CORRECTION = "PENDING_CORRECTION"

    class Source(Enum):
        """Render an Enum of the Filing Sources."""

        COLIN = "COLIN"
        LEAR = "LEAR"

    class FilingTypes(str, Enum):
        """Render an Enum of all Filing Types."""

        ADMIN_FREEZE = "adminFreeze"
        ALTERATION = "alteration"
        AMALGAMATIONAPPLICATION = "amalgamationApplication"
        AMENDEDAGM = "amendedAGM"
        AMENDEDANNUALREPORT = "amendedAnnualReport"
        AMENDEDCHANGEOFDIRECTORS = "amendedChangeOfDirectors"
        ANNUALREPORT = "annualReport"
        APPOINTRECEIVER = "appointReceiver"
        CHANGEOFADDRESS = "changeOfAddress"
        CHANGEOFDIRECTORS = "changeOfDirectors"
        CHANGEOFNAME = "changeOfName"
        CHANGEOFREGISTRATION = "changeOfRegistration"
        CONSENTCONTINUATIONOUT = "consentContinuationOut"
        CONTINUATIONOUT = "continuationOut"
        CONTINUEDOUT = "continuedOut"
        CONVERSION = "conversion"
        CORRECTION = "correction"
        COURTORDER = "courtOrder"
        DISSOLUTION = "dissolution"
        DISSOLVED = "dissolved"
        INCORPORATIONAPPLICATION = "incorporationApplication"
        PUTBACKON = "putBackOn"
        REGISTRARSNOTATION = "registrarsNotation"
        REGISTRARSORDER = "registrarsOrder"
        REGISTRATION = "registration"
        RESTORATION = "restoration"
        RESTORATIONAPPLICATION = "restorationApplication"
        SPECIALRESOLUTION = "specialResolution"
        TRANSITION = "transition"

    # TODO: get legal types from defined class once table is made (getting it from Business causes circ import)
    FILINGS = {
        "affidavit": {
            "name": "affidavit",
            "title": "Affidavit",
            "codes": {"CP": "AFDVT"},
        },
        "agmExtension": {
            "name": "agmExtension",
            "title": "AGM Extension",
            "codes": {"BC": "AGMDT", "BEN": "AGMDT", "ULC": "AGMDT", "CC": "AGMDT"},
        },
        "agmLocationChange": {
            "name": "agmLocationChange",
            "title": "AGM Change of Location",
            "codes": {"BC": "AGMLC", "BEN": "AGMLC", "ULC": "AGMLC", "CC": "AGMLC"},
        },
        "alteration": {
            "name": "alteration",
            "title": "Notice of Alteration Filing",
            "codes": {"BC": "ALTER", "BEN": "ALTER", "ULC": "ALTER", "CC": "ALTER"},
        },
        "amalgamationApplication": {
            "name": "amalgamationApplication",
            "temporaryCorpTypeCode": "ATMP",
            "regular": {
                "name": "regularAmalgamation",
                "title": "Regular Amalgamation",
                "codes": {"BEN": "AMALR", "BC": "AMALR", "ULC": "AMALR", "CC": "AMALR"},
            },
            "vertical": {
                "name": "verticalAmalgamation",
                "title": "Vertical Amalgamation",
                "codes": {"BEN": "AMALV", "BC": "AMALV", "ULC": "AMALV", "CC": "AMALV"},
            },
            "horizontal": {
                "name": "horizontalAmalgamation",
                "title": "Horizontal Amalgamation",
                "codes": {"BEN": "AMALH", "BC": "AMALH", "ULC": "AMALH", "CC": "AMALH"},
            },
        },
        "annualReport": {
            "name": "annualReport",
            "title": "Annual Report Filing",
            "codes": {
                "CP": "OTANN",
                "BEN": "BCANN",
                "BC": "BCANN",
                "ULC": "BCANN",
                "CC": "BCANN",
            },
        },
        "changeOfAddress": {
            "name": "changeOfAddress",
            "title": "Change of Address Filing",
            "codes": {
                "CP": "OTADD",
                "BEN": "BCADD",
                "BC": "BCADD",
                "ULC": "BCADD",
                "CC": "BCADD",
            },
        },
        "changeOfDirectors": {
            "name": "changeOfDirectors",
            "title": "Change of Directors Filing",
            "codes": {
                "CP": "OTCDR",
                "BEN": "BCCDR",
                "BC": "BCCDR",
                "ULC": "BCCDR",
                "CC": "BCCDR",
            },
            "free": {
                "codes": {
                    "CP": "OTFDR",
                    "BEN": "BCFDR",
                    "BC": "BCFDR",
                    "ULC": "BCFDR",
                    "CC": "BCFDR",
                }
            },
        },
        "changeOfName": {
            "name": "changeOfName",
            "title": "Change of Name Filing",
            "codes": {
                "CP": "OTCON",
            },
        },
        "changeOfRegistration": {
            "name": "changeOfRegistration",
            "title": "Change of Registration",
            "codes": {"SP": "FMCHANGE", "GP": "FMCHANGE"},
        },
        "consentContinuationOut": {
            "name": "consentContinuationOut",
            "title": "Consent Continuation Out",
            "codes": {"BC": "CONTO", "BEN": "CONTO", "ULC": "CONTO", "CC": "CONTO"},
        },
        "continuationOut": {
            "name": "continuationOut",
            "title": "Continuation Out",
            "codes": {"BC": "COUTI", "BEN": "COUTI", "ULC": "COUTI", "CC": "COUTI"},
        },
        "conversion": {
            "name": "conversion",
            "title": "Conversion Ledger",
            "codes": {"SP": "FMCONV", "GP": "FMCONV"},
        },
        "correction": {
            "name": "correction",
            "title": "Correction",
            "codes": {
                "BEN": "CRCTN",
                "BC": "CRCTN",
                "ULC": "CRCTN",
                "CC": "CRCTN",
                "CP": "CRCTN",
                "SP": "FMCORR",
                "GP": "FMCORR",
            },
        },
        "dissolution": {
            "name": "dissolution",
            "voluntary": {
                "name": "voluntary",
                "title": "Voluntary Dissolution",
                "codes": {
                    "CP": "DIS_VOL",
                    "BC": "DIS_VOL",
                    "BEN": "DIS_VOL",
                    "ULC": "DIS_VOL",
                    "CC": "DIS_VOL",
                    "LLC": "DIS_VOL",
                    "SP": "DIS_VOL",
                    "GP": "DIS_VOL",
                },
            },
            "administrative": {
                "name": "administrative",
                "title": "Administrative Dissolution",
                "codes": {
                    "CP": "DIS_ADM",
                    "BC": "DIS_ADM",
                    "BEN": "DIS_ADM",
                    "ULC": "DIS_ADM",
                    "CC": "DIS_ADM",
                    "LLC": "DIS_ADM",
                    "SP": "DIS_ADM",
                    "GP": "DIS_ADM",
                },
            },
        },
        "incorporationApplication": {
            "name": "incorporationApplication",
            "title": "Incorporation Application",
            "codes": {
                "BEN": "BCINC",
                "BC": "BCINC",
                "ULC": "BCINC",
                "CC": "BCINC",
                "CP": "OTINC",
            },
            "temporaryCorpTypeCode": "TMP",
        },
        "registration": {
            "name": "registration",
            "title": "Registration",
            "codes": {"SP": "FRREG", "GP": "FRREG"},
            "temporaryCorpTypeCode": "RTMP",
        },
        "restoration": {
            "name": "restoration",
            "fullRestoration": {
                "name": "fullRestoration",
                "title": "Full Restoration",
                "codes": {"BC": "RESTF", "BEN": "RESTF", "ULC": "RESTF", "CC": "RESTF"},
            },
            "limitedRestoration": {
                "name": "limitedRestoration",
                "title": "Limited Restoration",
                "codes": {"BC": "RESTL", "BEN": "RESTL", "ULC": "RESTL", "CC": "RESTL"},
            },
            "limitedRestorationExtension": {
                "name": "limitedRestorationExtension",
                "title": "Limited Restoration Extension",
                "codes": {"BC": "RESXL", "BEN": "RESXL", "ULC": "RESXL", "CC": "RESXL"},
            },
            "limitedRestorationToFull": {
                "name": "limitedRestorationToFull",
                "title": "Limited Restoration To Full",
                "codes": {"BC": "RESXF", "BEN": "RESXF", "ULC": "RESXF", "CC": "RESXF"},
            },
        },
        "specialResolution": {
            "name": "specialResolution",
            "title": "Special Resolution",
            "codes": {"CP": "SPRLN"},
        },
        "transition": {
            "name": "transition",
            "title": "Transition",
            "codes": {"BC": "TRANS", "BEN": "TRANS", "ULC": "TRANS", "CC": "TRANS"},
        },
        # changing the structure of fee code in courtOrder/registrarsNotation/registrarsOrder
        # for all the business the fee code remain same as NOFEE (Staff)
        "adminFreeze": {
            "name": "adminFreeze",
            "title": "Admin Freeze",
            "code": "NOFEE",
        },
        "courtOrder": {"name": "courtOrder", "title": "Court Order", "code": "NOFEE"},
        "putBackOn": {"name": "putBackOn", "title": "Put Back On", "code": "NOFEE"},
        "registrarsNotation": {
            "name": "registrarsNotation",
            "title": "Registrars Notation",
            "code": "NOFEE",
        },
        "registrarsOrder": {
            "name": "registrarsOrder",
            "title": "Registrars Order",
            "code": "NOFEE",
        },
    }

    FILING_SUB_TYPE_KEYS: Final = {
        # FUTURE: uncomment and update such that FEE codes can be defined like restoration sub-types.  Tests were
        #  breaking and more testing was req'd so did not make refactor when introducing this dictionary.
        "dissolution": "dissolutionType",
        "restoration": "type",
        "amalgamationApplication": "type",
    }

    __tablename__ = "filings"
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
        "include_properties": [
            "id",
            "_completion_date",
            "_filing_date",
            "_filing_json",
            "_filing_type",
            "_filing_sub_type",
            "_meta_data",
            "_payment_completion_date",
            "_payment_status_code",
            "_payment_token",
            "_source",
            "_status",
            "approval_type",
            "application_date",
            "colin_only",
            "court_order_date",
            "court_order_effect_of_order",
            "court_order_file_number",
            "deletion_locked",
            "effective_date",
            "legal_entity_id",
            "notice_date",
            "order_details",
            "paper_only",
            "parent_filing_id",  # FUTURE: this id should no longer be used for correction filings and will be removed
            "payment_account",
            "submitter_id",
            "submitter_roles",
            "tech_correction_json",
            "temp_reg",
            "transaction_id",
            "alternate_name_id",
        ]
    }

    id = db.Column(db.Integer, primary_key=True)
    _completion_date = db.Column("completion_date", db.DateTime(timezone=True))
    _filing_date = db.Column("filing_date", db.DateTime(timezone=True), default=datetime.utcnow)
    _filing_type = db.Column("filing_type", db.String(30))
    _filing_sub_type = db.Column("filing_sub_type", db.String(30))
    _filing_json = db.Column("filing_json", JSONB)
    _meta_data = db.Column("meta_data", JSONB)
    _payment_status_code = db.Column("payment_status_code", db.String(50))
    _payment_token = db.Column("payment_id", db.String(4096))
    _payment_completion_date = db.Column("payment_completion_date", db.DateTime(timezone=True))
    _status = db.Column("status", db.String(20), default=Status.DRAFT)
    _source = db.Column("source", db.String(15), default=Source.LEAR.value)
    paper_only = db.Column("paper_only", db.Boolean, unique=False, default=False)
    colin_only = db.Column("colin_only", db.Boolean, unique=False, default=False)
    payment_account = db.Column("payment_account", db.String(30))
    effective_date = db.Column("effective_date", db.DateTime(timezone=True), default=datetime.utcnow)
    submitter_roles = db.Column("submitter_roles", db.String(200))
    tech_correction_json = db.Column("tech_correction_json", JSONB)
    court_order_file_number = db.Column("court_order_file_number", db.String(20))
    court_order_date = db.Column("court_order_date", db.DateTime(timezone=True), default=None)
    court_order_effect_of_order = db.Column("court_order_effect_of_order", db.String(500))
    order_details = db.Column("order_details", db.String(2000))
    deletion_locked = db.Column("deletion_locked", db.Boolean, unique=False, default=False)
    approval_type = db.Column("approval_type", db.String(15))
    application_date = db.Column("application_date", db.DateTime(timezone=True))
    notice_date = db.Column("notice_date", db.DateTime(timezone=True))

    transaction_id = db.Column("transaction_id", db.Integer)
    # # relationships
    # transaction_id = db.Column('transaction_id', db.BigInteger,
    #    db.ForeignKey('transaction.id'))
    legal_entity_id = db.Column("legal_entity_id", db.Integer, db.ForeignKey("legal_entities.id"))
    alternate_name_id = db.Column("alternate_name_id", db.Integer, db.ForeignKey("alternate_names.id"))
    temp_reg = db.Column("temp_reg", db.String(10), db.ForeignKey("registration_bootstrap.identifier"))
    submitter_id = db.Column("submitter_id", db.Integer, db.ForeignKey("users.id"))

    filing_submitter = db.relationship(
        "User",
        backref=backref("filing_submitter", uselist=False),
        foreign_keys=[submitter_id],
    )

    colin_event_ids = db.relationship("ColinEventId", lazy="select")

    comments = db.relationship("Comment", lazy="dynamic")
    documents = db.relationship("Document", lazy="dynamic")
    filing_entity_roles = db.relationship(
        "EntityRole", lazy="dynamic", primaryjoin="(Filing.id==EntityRole.filing_id)", overlaps="filing"
    )

    # FUTURE: parent_filing_id and parent_filing should no longer be used for correction filings and will be removed
    parent_filing_id = db.Column(db.Integer, db.ForeignKey("filings.id"))
    parent_filing = db.relationship("Filing", remote_side=[id], backref=backref("children"))

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
        if self.locked or (self._payment_token and self._filing_json):
            self._payment_completion_date = value
            # if self.effective_date is None or \
            #         self.effective_date <= self._payment_completion_date:
            #     self._status = Filing.Status.COMPLETED.value
        else:
            raise BusinessException(
                error="Payment Dates cannot set for unlocked filings unless the filing hasn't been saved yet.",
                status_code=HTTPStatus.FORBIDDEN,
            )

    @property
    def status(self):
        """Property containing the filing status."""
        # pylint: disable=W0212; prevent infinite loop
        # FUTURE: parent_filing_id and parent_filing should no longer be used for correction filings and will be removed
        if (
            self._status == Filing.Status.COMPLETED
            and self.parent_filing_id
            and self.parent_filing._status == Filing.Status.COMPLETED
        ):
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
                error="Tried to update the filing with an invalid source.",
                status_code=HTTPStatus.BAD_REQUEST,
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
            self._filing_type = json_data.get("filing", {}).get("header", {}).get("name")
            if not self._filing_type:
                raise Exception  # pylint: disable=broad-exception-raised
        except Exception as err:
            raise BusinessException(error="No filings found.", status_code=HTTPStatus.UNPROCESSABLE_ENTITY) from err

        self._filing_sub_type = self.get_filings_sub_type(self._filing_type, json_data)

        if self._payment_token:
            valid, err = rsbc_schemas.validate(json_data, "filing")
            if not valid:
                self._filing_type = None
                self._payment_token = None
                errors = build_schema_error_response(err)
                raise BusinessException(error=f"{errors}", status_code=HTTPStatus.UNPROCESSABLE_ENTITY)

            self._status = Filing.Status.PENDING.value
        self._filing_json = json_data

    @property
    def json_legal_type(self):
        """Return the legal type from a filing_json or None."""
        filing = self._filing_json.get("filing", {})
        legal_type = filing.get("business", {}).get("legalType", None)
        if legal_type is None:
            legal_type = filing.get(self.filing_type, {}).get("nameRequest").get("legalType", None)
        return legal_type

    @property
    def json_nr(self):
        """Return the NR Number from a filing_json or None."""
        return (
            self._filing_json.get("filing", {}).get(self.filing_type, {}).get("nameRequest", {}).get("nrNumber", None)
        )

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
            self.effective_date is None
            or (
                self.payment_completion_date
                and self.effective_date  # pylint: disable=W0143
                < self.payment_completion_date  # pylint: disable=W0143; hybrid property  # noqa: E501
            )
        ):
            self.effective_date = self.payment_completion_date

    def effective_date_can_be_before_payment_completion_date(self, business_type):
        """For AR or COD filings on CP or BEN then the effective date can be before the payment date."""
        return self.filing_type in (
            Filing.FILINGS["annualReport"].get("name"),
            Filing.FILINGS["changeOfDirectors"].get("name"),
        ) and business_type in {"CP", "BEN"}

    @staticmethod
    def _raise_default_lock_exception():
        raise BusinessException(
            error="Filings cannot be changed after the invoice is created.",
            status_code=HTTPStatus.FORBIDDEN,
        )

    @property
    def is_corrected(self):
        """Has this filing been corrected."""
        if (
            # FUTURE: parent_filing should no longer be used for correction filings and will be removed
            self.parent_filing
            and self.parent_filing.filing_type == Filing.FILINGS["correction"].get("name")
            and self.parent_filing.status == Filing.Status.COMPLETED.value
        ):
            return True
        return False

    @property
    def is_correction_pending(self):
        """Is there a pending correction for this filing."""
        if (
            # FUTURE: parent_filing should no longer be used for correction filings and will be removed
            self.parent_filing
            and self.parent_filing.filing_type == Filing.FILINGS["correction"].get("name")
            and self.parent_filing.status == Filing.Status.PENDING_CORRECTION.value
        ):
            return True
        return False

    @hybrid_property
    def comments_count(self):
        """Return the number of commentson this filing."""
        return self.comments.count()

    @comments_count.expression
    def comments_count(self):
        """Return comments count expression for this filing."""
        return (
            select([func.count(Comment.legal_entity_id)])  # pylint: disable=not-callable
            .where(Comment.legal_entity_id == self.id)
            .label("comments_count")
        )

    # json serializer
    @property
    def json(self):
        """Return a json representation of this object."""
        try:
            json_submission = copy.deepcopy(self.filing_json)
            json_submission["filing"]["header"]["date"] = self._filing_date.isoformat()
            json_submission["filing"]["header"]["filingId"] = self.id
            json_submission["filing"]["header"]["name"] = self.filing_type
            json_submission["filing"]["header"]["status"] = self.status
            json_submission["filing"]["header"]["availableOnPaperOnly"] = self.paper_only
            json_submission["filing"]["header"]["inColinOnly"] = self.colin_only
            json_submission["filing"]["header"]["deletionLocked"] = self.deletion_locked

            if self.effective_date:  # pylint: disable=using-constant-test
                json_submission["filing"]["header"][
                    "effectiveDate"
                ] = self.effective_date.isoformat()  # noqa: E501 pylint: disable=no-member, line-too-long
            if self._payment_status_code:
                json_submission["filing"]["header"]["paymentStatusCode"] = self.payment_status_code
            if self._payment_token:
                json_submission["filing"]["header"]["paymentToken"] = self.payment_token
            if self.submitter_id:
                json_submission["filing"]["header"]["submitter"] = self.filing_submitter.username
            if self.payment_account:
                json_submission["filing"]["header"]["paymentAccount"] = self.payment_account

            # add colin_event_ids
            json_submission["filing"]["header"]["colinIds"] = ColinEventId.get_by_filing_id(self.id)

            # add comments
            json_submission["filing"]["header"]["comments"] = [comment.json for comment in self.comments]

            # add affected filings list
            json_submission["filing"]["header"]["affectedFilings"] = [filing.id for filing in self.children]

            # add corrected flags
            json_submission["filing"]["header"]["isCorrected"] = self.is_corrected
            json_submission["filing"]["header"]["isCorrectionPending"] = self.is_correction_pending

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
        """Return a Filing by it's payment token."""
        q = db.session.query(Filing).filter(Filing.temp_reg == temp_reg_id)

        if filing_id:
            q.filter(Filing.id == filing_id)

        filing = q.one_or_none()
        return filing

    @staticmethod
    def get_filing_by_payment_token(token: str):
        """Return a Filing by it's payment token."""
        filing = db.session.query(Filing).filter(Filing.payment_token == token).one_or_none()
        return filing

    @staticmethod
    def get_filings_by_status(business: any, status: list, after_date: date = None):
        """Return the filings with statuses in the status array input."""
        business_attr = Filing.alternate_name_id if business.is_alternate_name_entity else Filing.legal_entity_id
        query = (
            db.session.query(Filing)
            .filter(business_attr == business.id)
            .filter(Filing._status.in_(status))
            .order_by(Filing._filing_date.desc(), Filing.effective_date.desc())
        )  # pylint: disable=no-member;
        # member provided via SQLAlchemy

        if after_date:
            query = query.filter(Filing._filing_date >= after_date)

        return query.all()

    @staticmethod
    def get_incomplete_filings_by_type(business: any, filing_type: str):
        """Return the incomplete filings of a particular type."""
        business_attr = Filing.alternate_name_id if business.is_alternate_name_entity else Filing.legal_entity_id
        filings = (
            db.session.query(Filing)
            .filter(business_attr == business.id)
            .filter(Filing._filing_type == filing_type)
            .filter(Filing._status != Filing.Status.COMPLETED.value)
            .order_by(desc(Filing.filing_date))
            .all()
        )
        return filings

    @staticmethod
    def get_filings_by_types(business: any, filing_types):
        """Return the completed filings of a particular type."""
        business_attr = Filing.alternate_name_id if business.is_alternate_name_entity else Filing.legal_entity_id
        filings = (
            db.session.query(Filing)
            .filter(business_attr == business.id)
            .filter(Filing._filing_type.in_(filing_types))
            .filter(Filing._status == Filing.Status.COMPLETED.value)
            .order_by(desc(Filing.effective_date))
            .all()
        )
        return filings

    @staticmethod
    def get_incomplete_filings_by_types(business: any, filing_types: list, excluded_statuses: list = None):
        """Return the filings of particular types and statuses.

        excluded_statuses is a list of filing statuses that will be excluded from the query for incomplete filings
        """
        excluded_statuses = [] if excluded_statuses is None else excluded_statuses

        business_attr = Filing.alternate_name_id if business.is_alternate_name_entity else Filing.legal_entity_id
        filings = (
            db.session.query(Filing)
            .filter(business_attr == business.id)
            .filter(Filing._filing_type.in_(filing_types))
            .filter(Filing._status != Filing.Status.COMPLETED.value)
            .filter(not_(Filing._status.in_(excluded_statuses)))
            .order_by(desc(Filing.effective_date))
            .all()
        )
        return filings

    @staticmethod
    def get_filings_by_type_pairs(
        business: any,
        filing_type_pairs: list,
        status: list,
        return_unique_pairs=False,
    ):
        """Return the filings of particular filing type/sub-type pairs as well as statuses.

        If return_unique_pairs is True, only return one instance of each filing type/sub-type pair.
        """
        business_attr = Filing.alternate_name_id if business.is_alternate_name_entity else Filing.legal_entity_id
        filing_type_conditions = [
            and_(
                Filing._filing_type == filing_type,
                Filing._filing_sub_type == filing_sub_type,
            ).self_group()
            for filing_type, filing_sub_type in filing_type_pairs
        ]

        base_query = (
            db.session.query(Filing)
            .filter(business_attr == business.id)
            .filter(Filing._status.in_(status))
            .filter(or_(*filing_type_conditions))
        )

        # pylint: disable=W0212; prevent infinite loop
        if return_unique_pairs:
            subquery = (
                base_query.with_entities(
                    Filing._filing_type,
                    Filing._filing_sub_type,
                    func.max(Filing.id).label("id"),
                )
                .group_by(Filing._filing_type, Filing._filing_sub_type)
                .subquery()
            )
            query = base_query.join(subquery, and_(Filing.id == subquery.c.id))
        else:
            query = base_query

        filings = query.all()
        return filings

    @staticmethod
    def get_a_businesses_most_recent_filing_of_a_type(business: any, filing_type: str, filing_sub_type: str = None):
        """Return the filings of a particular type."""
        business_attr = Filing.alternate_name_id if business.is_alternate_name_entity else Filing.legal_entity_id
        max_filing = (
            db.session.query(db.func.max(Filing._filing_date).label("last_filing_date"))
            .filter(Filing._filing_type == filing_type)
            .filter(business_attr == business.id)
        )
        if filing_sub_type:
            max_filing = max_filing.filter(Filing._filing_sub_type == filing_sub_type)
        max_filing = max_filing.subquery()

        filing = (
            Filing.query.join(max_filing, Filing._filing_date == max_filing.c.last_filing_date)
            .filter(business_attr == business.id)
            .filter(Filing._filing_type == filing_type)
            .filter(Filing._status == Filing.Status.COMPLETED.value)
        )
        if filing_sub_type:
            filing = filing.filter(Filing._filing_sub_type == filing_sub_type)

        return filing.one_or_none()

    @staticmethod
    def get_most_recent_legal_filing(business: any, filing_type: str = None):
        """Return the most recent filing containing the legal_filing type."""
        business_attribute = Filing.legal_entity_id if business.is_legal_entity else Filing.alternate_name_id

        query = (
            db.session.query(db.func.max(Filing._filing_date).label("last_filing_date"))
            .filter(business_attribute == business.id)
            .filter(Filing._status == Filing.Status.COMPLETED.value)
        )
        if filing_type:
            expr = Filing._filing_json[("filing", filing_type)]
            query = query.filter(
                or_(
                    Filing._filing_type == filing_type,
                    expr.label("legal_filing_type").isnot(None),
                )
            )
        max_filing = query.subquery()

        filing = (
            Filing.query.join(max_filing, Filing._filing_date == max_filing.c.last_filing_date)
            .filter(business_attribute == business.id)
            .filter(Filing._status == Filing.Status.COMPLETED.value)
            .order_by(Filing.id.desc())
        )

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
        from .legal_entity import LegalEntity  # noqa: F401; pylint: disable=import-outside-toplevel

        filings = (
            db.session.query(Filing)
            .join(LegalEntity, Filing.legal_entity_id == LegalEntity.id)
            .filter(
                ~LegalEntity.entity_type.in_(
                    [
                        LegalEntity.EntityTypes.SOLE_PROP.value,
                        LegalEntity.EntityTypes.PARTNERSHIP.value,
                    ]
                ),
                Filing.colin_event_ids == None,  # pylint: disable=singleton-comparison # noqa: E711;
                Filing._status == Filing.Status.COMPLETED.value,
                Filing.effective_date != None,  # pylint: disable=singleton-comparison # noqa: E711;
            )
            .order_by(Filing.filing_date)
            .all()
        )
        return filings

    @staticmethod
    def get_all_filings_by_status(status):
        """Return all filings based on status."""
        filings = (
            db.session.query(Filing).filter(Filing._status == status).all()
        )  # pylint: disable=singleton-comparison # noqa: E711;
        return filings

    @staticmethod
    def get_previous_completed_filing(filing):
        """Return the previous completed filing."""
        if filing.legal_entity_id:
            business_attr = Filing.legal_entity_id
            business_attr_value = filing.legal_entity_id
        else:
            business_attr = Filing.alternate_name_id
            business_attr_value = filing.alternate_name_id

        filings = (
            db.session.query(Filing)
            .filter(business_attr == business_attr_value)
            .filter(Filing._status == Filing.Status.COMPLETED.value)
            .filter(Filing.id < filing.id)
            .filter(Filing.effective_date < filing.effective_date)
            .order_by(Filing.effective_date.desc())
            .all()
        )
        if filings:
            return filings[0]
        return None

    @staticmethod
    def has_completed_filing(business: any, filing_type: str) -> bool:
        """Return whether a completed filing of a given filing type exists."""
        business_attribute = Filing.legal_entity_id if business.is_legal_entity else Filing.alternate_name_id
        query = (
            db.session.query(Filing)
            .filter(business_attribute == business.id)
            .filter(Filing._filing_type == filing_type)
            .filter(Filing._status == Filing.Status.COMPLETED.value)
        )
        exists_stmt = query.exists()
        filing_exists = db.session.query(exists_stmt).scalar()
        return filing_exists

    @staticmethod
    def get_filings_sub_type(filing_type: str, filing_json: dict):
        """Return sub-type from filing json if sub-type exists for filing type."""
        filing_sub_type_key = Filing.FILING_SUB_TYPE_KEYS.get(filing_type)
        if filing_sub_type_key:
            filing_sub_type = filing_json["filing"][filing_type][filing_sub_type_key]
            return filing_sub_type

        return None

    @staticmethod
    def get_fee_code(legal_type: str, filing_type: str, filing_sub_type: str = None):
        """Return fee code for filing."""
        filing_dict = Filing.FILINGS.get(filing_type, None)

        if filing_sub_type:
            fee_code = filing_dict[filing_sub_type]["codes"].get(legal_type, None)
        else:
            if fee_code := filing_dict.get("code", None):
                return fee_code
            fee_code = filing_dict["codes"].get(legal_type, None)

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
            raise BusinessException(error="Deletion not allowed.", status_code=HTTPStatus.FORBIDDEN)
        db.session.delete(self)
        db.session.commit()

    def reset_filing_to_draft(self):
        """Reset Filing to draft and remove payment token."""
        self._status = Filing.Status.DRAFT.value
        self._payment_token = None
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
        for k in filing["filing"].keys():  # pylint: disable=unsubscriptable-object
            if Filing.FILINGS.get(k, None):
                legal_filings.append(
                    {k: copy.deepcopy(filing["filing"].get(k))}  # pylint: disable=unsubscriptable-object
                )

        return legal_filings


@event.listens_for(Filing, "before_delete")
def block_filing_delete_listener_function(mapper, connection, target):  # pylint: disable=unused-argument
    """Raise an error when a delete is attempted on a Filing."""
    filing = target

    if filing.locked or filing.deletion_locked:
        raise BusinessException(error="Deletion not allowed.", status_code=HTTPStatus.FORBIDDEN)


@event.listens_for(Filing, "before_insert")
@event.listens_for(Filing, "before_update")
def receive_before_change(mapper, connection, target):  # pylint: disable=unused-argument; SQLAlchemy callback signature
    """Set the state of the filing, based upon column values."""
    filing = target

    # skip this status updater if the flag is set
    # Scenario: if this is a correction filing, and would have been set to COMPLETE by the entity filer, leave it as is
    # because it's been set to PENDING_CORRECTION by the entity filer.
    if hasattr(filing, "skip_status_listener") and filing.skip_status_listener:
        return
    # changes are part of the class and are not externalized
    if filing.filing_type == "lear_epoch":
        filing._status = Filing.Status.EPOCH.value  # pylint: disable=protected-access
    elif filing.transaction_id:
        filing._status = Filing.Status.COMPLETED.value  # pylint: disable=protected-access
    elif filing.payment_completion_date or filing.source == Filing.Source.COLIN.value:
        filing._status = Filing.Status.PAID.value  # pylint: disable=protected-access
    elif filing.payment_token:
        filing._status = Filing.Status.PENDING.value  # pylint: disable=protected-access
    else:
        filing._status = Filing.Status.DRAFT.value  # pylint: disable=protected-access
