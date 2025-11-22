# Copyright © 2021 Province of British Columbia
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
"""Name Request Type mapping service.

Provides an endpoint to query/match NR Type to Entity Type mappings.
"""
from enum import Enum
from http import HTTPStatus

from flask import request
from flask_restx import Namespace, Resource

from legal_api.models import Business

API = Namespace("nrTypeMap", description="NR Type mapping service")


class RequestActions(Enum):
    """Render an Enum of the Request Actions. Should match RequestAction enum in namex project."""

    ACHG = "ACHG"
    AML = "AML"  # amalgamate
    AS = "AS"  # assumed
    CHG = "CHG"  # change (ie, alter)
    CNV = "CNV"  # convert
    MVE = "MVE"  # move
    NEW = "NEW"  # new business
    NEW_AML = "NEW_AML"  # new or amalgamate
    REH = "REH"
    REN = "REN"  # renew
    REST = "REST"  # restore


@API.route("", methods=["GET"])
@API.doc(params={
    "nrTypeCd": {"description": "Optional NR Type code.", "example": "CR"},
    "entityTypeCd": {"description": "Optional Entity Type code.", "example": "BC"},
    "requestActionCd": {"description": "Optional Request Action code.", "example": "NEW"}
})
class NrTypeMap(Resource):
    """NR Type mapping service."""

    @staticmethod
    def get():
        """Return a list of mappings matching any query params."""
        # get query params
        nr_type_cd = (request.args.get("nrTypeCd", None).upper()) \
            if request.args.get("nrTypeCd", None) else None
        entity_type_cd = (request.args.get("entityTypeCd", None).upper()) \
            if request.args.get("entityTypeCd", None) else None
        request_action_cd = (request.args.get("requestActionCd", None).upper()) \
            if request.args.get("requestActionCd", None) else None

        # build list of tuples
        # should match Request Type Mapping in namex project
        # NB: commented out tuples that exist in namex but are not yet supported by Lear
        request_type_mapping = [
            # NR Type Code, Legal Type the NR type code is valid for, Filing Type we can do
            ("CR", Business.LegalTypes.COMP.value, RequestActions.NEW_AML.value),
            ("CR", Business.LegalTypes.COMP.value, RequestActions.NEW.value),
            ("CR", Business.LegalTypes.COMP.value, RequestActions.AML.value),
            ("CCR", Business.LegalTypes.COMP.value, RequestActions.CHG.value),
            ("CT", Business.LegalTypes.COMP.value, RequestActions.MVE.value),
            ("RCR", Business.LegalTypes.COMP.value, RequestActions.REST.value),
            ("RCR", Business.LegalTypes.COMP.value, RequestActions.REH.value),
            ("RCR", Business.LegalTypes.COMP.value, RequestActions.REN.value),
            ("BECR", Business.LegalTypes.COMP.value, RequestActions.CNV.value),
            ("ULCB", Business.LegalTypes.COMP.value, RequestActions.CNV.value),
            # ('XCR', Business.LegalTypes.XPRO_CORPORATION.value, RequestActions.NEW_AML.value),
            # ('XCR', Business.LegalTypes.XPRO_CORPORATION.value, RequestActions.NEW.value),
            # ('XCR', Business.LegalTypes.XPRO_CORPORATION.value, RequestActions.AML.value),
            # ('XCCR', Business.LegalTypes.XPRO_CORPORATION.value, RequestActions.CHG.value),
            # ('XRCR', Business.LegalTypes.XPRO_CORPORATION.value, RequestActions.REST.value),
            # ('XRCR', Business.LegalTypes.XPRO_CORPORATION.value, RequestActions.REH.value),
            # ('XRCR', Business.LegalTypes.XPRO_CORPORATION.value, RequestActions.REN.value),
            # ('AS', Business.LegalTypes.XPRO_CORPORATION.value, RequestActions.AS.value),
            ("LC", Business.LegalTypes.XPRO_LL_PARTNR.value, RequestActions.NEW.value),
            ("CLC", Business.LegalTypes.XPRO_LL_PARTNR.value, RequestActions.CHG.value),
            ("RLC", Business.LegalTypes.XPRO_LL_PARTNR.value, RequestActions.REST.value),
            ("RLC", Business.LegalTypes.XPRO_LL_PARTNR.value, RequestActions.REN.value),
            ("RLC", Business.LegalTypes.XPRO_LL_PARTNR.value, RequestActions.REH.value),
            ("AL", Business.LegalTypes.XPRO_LL_PARTNR.value, RequestActions.AS.value),
            ("FR", Business.LegalTypes.SOLE_PROP.value, RequestActions.NEW.value),
            ("FR", Business.LegalTypes.PARTNERSHIP.value, RequestActions.NEW.value),
            # ('FR', Business.LegalTypes.DOING_BUSINESS_AS.value, RequestActions.NEW.value),
            ("CFR", Business.LegalTypes.SOLE_PROP.value, RequestActions.CHG.value),
            ("CFR", Business.LegalTypes.PARTNERSHIP.value, RequestActions.CHG.value),
            # ('CFR', Business.LegalTypes.DOING_BUSINESS_AS.value, RequestActions.CHG.value),
            ("LL", Business.LegalTypes.LL_PARTNERSHIP.value, RequestActions.NEW.value),
            ("CLL", Business.LegalTypes.LL_PARTNERSHIP.value, RequestActions.CHG.value),
            ("XLL", Business.LegalTypes.XPRO_LL_PARTNR.value, RequestActions.NEW.value),
            ("XCLL", Business.LegalTypes.XPRO_LL_PARTNR.value, RequestActions.CHG.value),
            ("LP", Business.LegalTypes.LIM_PARTNERSHIP.value, RequestActions.NEW.value),
            ("CLP", Business.LegalTypes.LIM_PARTNERSHIP.value, RequestActions.CHG.value),
            ("XLP", Business.LegalTypes.XPRO_LIM_PARTNR.value, RequestActions.NEW.value),
            ("XCLP", Business.LegalTypes.XPRO_LIM_PARTNR.value, RequestActions.CHG.value),
            ("SO", Business.LegalTypes.SOCIETY.value, RequestActions.NEW.value),
            ("ASO", Business.LegalTypes.SOCIETY.value, RequestActions.AML.value),
            ("CSO", Business.LegalTypes.SOCIETY.value, RequestActions.CHG.value),
            ("RSO", Business.LegalTypes.SOCIETY.value, RequestActions.REST.value),
            ("RSO", Business.LegalTypes.SOCIETY.value, RequestActions.REN.value),
            ("RSO", Business.LegalTypes.SOCIETY.value, RequestActions.REH.value),
            ("CTSO", Business.LegalTypes.SOCIETY.value, RequestActions.MVE.value),
            ("CSSO", Business.LegalTypes.SOCIETY.value, RequestActions.CNV.value),
            ("XSO", Business.LegalTypes.XPRO_SOCIETY.value, RequestActions.NEW.value),
            ("XCSO", Business.LegalTypes.XPRO_SOCIETY.value, RequestActions.CHG.value),
            ("XRSO", Business.LegalTypes.XPRO_SOCIETY.value, RequestActions.REST.value),
            ("XRSO", Business.LegalTypes.XPRO_SOCIETY.value, RequestActions.REH.value),
            ("XRSO", Business.LegalTypes.XPRO_SOCIETY.value, RequestActions.REN.value),
            ("XASO", Business.LegalTypes.XPRO_SOCIETY.value, RequestActions.AS.value),
            ("XCASO", Business.LegalTypes.XPRO_SOCIETY.value, RequestActions.ACHG.value),
            ("CP", Business.LegalTypes.COOP.value, RequestActions.NEW_AML.value),
            ("CP", Business.LegalTypes.COOP.value, RequestActions.NEW.value),
            ("CP", Business.LegalTypes.COOP.value, RequestActions.AML.value),
            ("CCP", Business.LegalTypes.COOP.value, RequestActions.CHG.value),
            ("CTC", Business.LegalTypes.COOP.value, RequestActions.MVE.value),
            ("RCP", Business.LegalTypes.COOP.value, RequestActions.REST.value),
            ("RCP", Business.LegalTypes.COOP.value, RequestActions.REH.value),
            ("RCP", Business.LegalTypes.COOP.value, RequestActions.REN.value),
            ("XCP", Business.LegalTypes.XPRO_COOP.value, RequestActions.NEW_AML.value),
            ("XCP", Business.LegalTypes.XPRO_COOP.value, RequestActions.NEW.value),
            ("XCP", Business.LegalTypes.XPRO_COOP.value, RequestActions.AML.value),
            ("XCCP", Business.LegalTypes.XPRO_COOP.value, RequestActions.CHG.value),
            ("XRCP", Business.LegalTypes.XPRO_COOP.value, RequestActions.REST.value),
            ("XRCP", Business.LegalTypes.XPRO_COOP.value, RequestActions.REH.value),
            ("XRCP", Business.LegalTypes.XPRO_COOP.value, RequestActions.REN.value),
            ("CC", Business.LegalTypes.BC_CCC.value, RequestActions.NEW_AML.value),
            ("CC", Business.LegalTypes.BC_CCC.value, RequestActions.NEW.value),
            ("CC", Business.LegalTypes.BC_CCC.value, RequestActions.AML.value),
            ("CCC", Business.LegalTypes.BC_CCC.value, RequestActions.CHG.value),
            ("CCCT", Business.LegalTypes.BC_CCC.value, RequestActions.MVE.value),
            ("RCC", Business.LegalTypes.BC_CCC.value, RequestActions.REST.value),
            ("RCC", Business.LegalTypes.BC_CCC.value, RequestActions.REH.value),
            ("RCC", Business.LegalTypes.BC_CCC.value, RequestActions.REN.value),
            ("CCV", Business.LegalTypes.BC_CCC.value, RequestActions.CNV.value),
            ("BECC", Business.LegalTypes.BC_CCC.value, RequestActions.CNV.value),
            ("UL", Business.LegalTypes.BC_ULC_COMPANY.value, RequestActions.NEW.value),
            ("UL", Business.LegalTypes.BC_ULC_COMPANY.value, RequestActions.AML.value),
            ("CUL", Business.LegalTypes.BC_ULC_COMPANY.value, RequestActions.CHG.value),
            ("ULCT", Business.LegalTypes.BC_ULC_COMPANY.value, RequestActions.MVE.value),
            ("RUL", Business.LegalTypes.BC_ULC_COMPANY.value, RequestActions.REST.value),
            ("RUL", Business.LegalTypes.BC_ULC_COMPANY.value, RequestActions.REH.value),
            ("RUL", Business.LegalTypes.BC_ULC_COMPANY.value, RequestActions.REN.value),
            ("UC", Business.LegalTypes.BC_ULC_COMPANY.value, RequestActions.CNV.value),
            ("FI", Business.LegalTypes.FINANCIAL.value, RequestActions.NEW.value),
            ("CFI", Business.LegalTypes.FINANCIAL.value, RequestActions.CHG.value),
            ("RFI", Business.LegalTypes.FINANCIAL.value, RequestActions.REST.value),
            ("RFI", Business.LegalTypes.FINANCIAL.value, RequestActions.REH.value),
            ("RFI", Business.LegalTypes.FINANCIAL.value, RequestActions.REN.value),
            ("PA", Business.LegalTypes.PRIVATE_ACT.value, RequestActions.NEW.value),
            ("PAR", Business.LegalTypes.PARISHES.value, RequestActions.NEW.value),
            ("BC", Business.LegalTypes.BCOMP.value, RequestActions.NEW.value),
            ("BEAM", Business.LegalTypes.BCOMP.value, RequestActions.AML.value),
            ("BEC", Business.LegalTypes.BCOMP.value, RequestActions.CHG.value),
            ("BECT", Business.LegalTypes.BCOMP.value, RequestActions.MVE.value),
            ("BERE", Business.LegalTypes.BCOMP.value, RequestActions.REST.value),
            ("BERE", Business.LegalTypes.BCOMP.value, RequestActions.REH.value),
            ("BERE", Business.LegalTypes.BCOMP.value, RequestActions.REN.value),
            ("BECV", Business.LegalTypes.BCOMP.value, RequestActions.CNV.value),
            ("ULBE", Business.LegalTypes.BCOMP.value, RequestActions.CNV.value)
        ]

        rv = []

        # get list of matching items
        for item in request_type_mapping:
            match0 = (not nr_type_cd) or (item[0] == nr_type_cd)
            match1 = (not entity_type_cd) or (item[1] == entity_type_cd)
            match2 = (not request_action_cd) or (item[2] == request_action_cd)

            if match0 and match1 and match2:
                rv.append({
                    "nrTypeCd": item[0],
                    "entityTypeCd": item[1],
                    "requestActionCd": item[2]
                })

        if not rv:
            return {"message": "no mappings found"}, HTTPStatus.NOT_FOUND

        return rv, HTTPStatus.OK
