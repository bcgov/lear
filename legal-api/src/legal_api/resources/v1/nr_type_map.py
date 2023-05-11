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

from legal_api.models import LegalEntity


API = Namespace('nrTypeMap', description='NR Type mapping service')


class RequestActions(Enum):
    """Render an Enum of the Request Actions. Should match RequestAction enum in namex project."""

    ACHG = 'ACHG'
    AML = 'AML'  # amalgamate
    AS = 'AS'  # assumed
    CHG = 'CHG'  # change (ie, alter)
    CNV = 'CNV'  # convert
    MVE = 'MVE'  # move
    NEW = 'NEW'  # new business
    NEW_AML = 'NEW_AML'  # new or amalgamate
    REH = 'REH'
    REN = 'REN'  # renew
    REST = 'REST'  # restore


@API.route('', methods=['GET'])
@API.doc(params={
    'nrTypeCd': {'description': 'Optional NR Type code.', 'example': 'CR'},
    'entityTypeCd': {'description': 'Optional Entity Type code.', 'example': 'BC'},
    'requestActionCd': {'description': 'Optional Request Action code.', 'example': 'NEW'}
})
class NrTypeMap(Resource):
    """NR Type mapping service."""

    @staticmethod
    def get():
        """Return a list of mappings matching any query params."""
        # get query params
        nr_type_cd = (request.args.get('nrTypeCd', None).upper()) \
            if request.args.get('nrTypeCd', None) else None
        entity_type_cd = (request.args.get('entityTypeCd', None).upper()) \
            if request.args.get('entityTypeCd', None) else None
        request_action_cd = (request.args.get('requestActionCd', None).upper()) \
            if request.args.get('requestActionCd', None) else None

        # build list of tuples
        # should match Request Type Mapping in namex project
        # NB: commented out tuples that exist in namex but are not yet supported by Lear
        request_type_mapping = [
            # NR Type Code, Legal Type the NR type code is valid for, Filing Type we can do
            ('CR', LegalEntity.EntityTypes.COMP.value, RequestActions.NEW_AML.value),
            ('CR', LegalEntity.EntityTypes.COMP.value, RequestActions.NEW.value),
            ('CR', LegalEntity.EntityTypes.COMP.value, RequestActions.AML.value),
            ('CCR', LegalEntity.EntityTypes.COMP.value, RequestActions.CHG.value),
            ('CT', LegalEntity.EntityTypes.COMP.value, RequestActions.MVE.value),
            ('RCR', LegalEntity.EntityTypes.COMP.value, RequestActions.REST.value),
            ('RCR', LegalEntity.EntityTypes.COMP.value, RequestActions.REH.value),
            ('RCR', LegalEntity.EntityTypes.COMP.value, RequestActions.REN.value),
            # ('XCR', LegalEntity.EntityTypes.XPRO_CORPORATION.value, RequestActions.NEW_AML.value),
            # ('XCR', LegalEntity.EntityTypes.XPRO_CORPORATION.value, RequestActions.NEW.value),
            # ('XCR', LegalEntity.EntityTypes.XPRO_CORPORATION.value, RequestActions.AML.value),
            # ('XCCR', LegalEntity.EntityTypes.XPRO_CORPORATION.value, RequestActions.CHG.value),
            # ('XRCR', LegalEntity.EntityTypes.XPRO_CORPORATION.value, RequestActions.REST.value),
            # ('XRCR', LegalEntity.EntityTypes.XPRO_CORPORATION.value, RequestActions.REH.value),
            # ('XRCR', LegalEntity.EntityTypes.XPRO_CORPORATION.value, RequestActions.REN.value),
            # ('AS', LegalEntity.EntityTypes.XPRO_CORPORATION.value, RequestActions.AS.value),
            ('LC', LegalEntity.EntityTypes.XPRO_LL_PARTNR.value, RequestActions.NEW.value),
            ('CLC', LegalEntity.EntityTypes.XPRO_LL_PARTNR.value, RequestActions.CHG.value),
            ('RLC', LegalEntity.EntityTypes.XPRO_LL_PARTNR.value, RequestActions.REST.value),
            ('RLC', LegalEntity.EntityTypes.XPRO_LL_PARTNR.value, RequestActions.REN.value),
            ('RLC', LegalEntity.EntityTypes.XPRO_LL_PARTNR.value, RequestActions.REH.value),
            ('AL', LegalEntity.EntityTypes.XPRO_LL_PARTNR.value, RequestActions.AS.value),
            ('FR', LegalEntity.EntityTypes.SOLE_PROP.value, RequestActions.NEW.value),
            ('FR', LegalEntity.EntityTypes.PARTNERSHIP.value, RequestActions.NEW.value),
            # ('FR', LegalEntity.EntityTypes.DOING_BUSINESS_AS.value, RequestActions.NEW.value),
            ('CFR', LegalEntity.EntityTypes.SOLE_PROP.value, RequestActions.CHG.value),
            ('CFR', LegalEntity.EntityTypes.PARTNERSHIP.value, RequestActions.CHG.value),
            # ('CFR', LegalEntity.EntityTypes.DOING_BUSINESS_AS.value, RequestActions.CHG.value),
            ('LL', LegalEntity.EntityTypes.LL_PARTNERSHIP.value, RequestActions.NEW.value),
            ('CLL', LegalEntity.EntityTypes.LL_PARTNERSHIP.value, RequestActions.CHG.value),
            ('XLL', LegalEntity.EntityTypes.XPRO_LL_PARTNR.value, RequestActions.NEW.value),
            ('XCLL', LegalEntity.EntityTypes.XPRO_LL_PARTNR.value, RequestActions.CHG.value),
            ('LP', LegalEntity.EntityTypes.LIM_PARTNERSHIP.value, RequestActions.NEW.value),
            ('CLP', LegalEntity.EntityTypes.LIM_PARTNERSHIP.value, RequestActions.CHG.value),
            ('XLP', LegalEntity.EntityTypes.XPRO_LIM_PARTNR.value, RequestActions.NEW.value),
            ('XCLP', LegalEntity.EntityTypes.XPRO_LIM_PARTNR.value, RequestActions.CHG.value),
            ('SO', LegalEntity.EntityTypes.SOCIETY.value, RequestActions.NEW.value),
            ('ASO', LegalEntity.EntityTypes.SOCIETY.value, RequestActions.AML.value),
            ('CSO', LegalEntity.EntityTypes.SOCIETY.value, RequestActions.CHG.value),
            ('RSO', LegalEntity.EntityTypes.SOCIETY.value, RequestActions.REST.value),
            ('RSO', LegalEntity.EntityTypes.SOCIETY.value, RequestActions.REN.value),
            ('RSO', LegalEntity.EntityTypes.SOCIETY.value, RequestActions.REH.value),
            ('CTSO', LegalEntity.EntityTypes.SOCIETY.value, RequestActions.MVE.value),
            ('CSSO', LegalEntity.EntityTypes.SOCIETY.value, RequestActions.CNV.value),
            ('XSO', LegalEntity.EntityTypes.XPRO_SOCIETY.value, RequestActions.NEW.value),
            ('XCSO', LegalEntity.EntityTypes.XPRO_SOCIETY.value, RequestActions.CHG.value),
            ('XRSO', LegalEntity.EntityTypes.XPRO_SOCIETY.value, RequestActions.REST.value),
            ('XRSO', LegalEntity.EntityTypes.XPRO_SOCIETY.value, RequestActions.REH.value),
            ('XRSO', LegalEntity.EntityTypes.XPRO_SOCIETY.value, RequestActions.REN.value),
            ('XASO', LegalEntity.EntityTypes.XPRO_SOCIETY.value, RequestActions.AS.value),
            ('XCASO', LegalEntity.EntityTypes.XPRO_SOCIETY.value, RequestActions.ACHG.value),
            ('CP', LegalEntity.EntityTypes.COOP.value, RequestActions.NEW_AML.value),
            ('CP', LegalEntity.EntityTypes.COOP.value, RequestActions.NEW.value),
            ('CP', LegalEntity.EntityTypes.COOP.value, RequestActions.AML.value),
            ('CCP', LegalEntity.EntityTypes.COOP.value, RequestActions.CHG.value),
            ('CTC', LegalEntity.EntityTypes.COOP.value, RequestActions.MVE.value),
            ('RCP', LegalEntity.EntityTypes.COOP.value, RequestActions.REST.value),
            ('RCP', LegalEntity.EntityTypes.COOP.value, RequestActions.REH.value),
            ('RCP', LegalEntity.EntityTypes.COOP.value, RequestActions.REN.value),
            ('XCP', LegalEntity.EntityTypes.XPRO_COOP.value, RequestActions.NEW_AML.value),
            ('XCP', LegalEntity.EntityTypes.XPRO_COOP.value, RequestActions.NEW.value),
            ('XCP', LegalEntity.EntityTypes.XPRO_COOP.value, RequestActions.AML.value),
            ('XCCP', LegalEntity.EntityTypes.XPRO_COOP.value, RequestActions.CHG.value),
            ('XRCP', LegalEntity.EntityTypes.XPRO_COOP.value, RequestActions.REST.value),
            ('XRCP', LegalEntity.EntityTypes.XPRO_COOP.value, RequestActions.REH.value),
            ('XRCP', LegalEntity.EntityTypes.XPRO_COOP.value, RequestActions.REN.value),
            ('CC', LegalEntity.EntityTypes.BC_CCC.value, RequestActions.NEW_AML.value),
            ('CC', LegalEntity.EntityTypes.BC_CCC.value, RequestActions.NEW.value),
            ('CC', LegalEntity.EntityTypes.BC_CCC.value, RequestActions.AML.value),
            ('CCV', LegalEntity.EntityTypes.BC_CCC.value, RequestActions.CNV.value),
            ('CCC', LegalEntity.EntityTypes.BC_CCC.value, RequestActions.CHG.value),
            ('CCCT', LegalEntity.EntityTypes.BC_CCC.value, RequestActions.MVE.value),
            ('RCC', LegalEntity.EntityTypes.BC_CCC.value, RequestActions.REST.value),
            ('RCC', LegalEntity.EntityTypes.BC_CCC.value, RequestActions.REH.value),
            ('RCC', LegalEntity.EntityTypes.BC_CCC.value, RequestActions.REN.value),
            ('UL', LegalEntity.EntityTypes.BC_ULC_COMPANY.value, RequestActions.NEW.value),
            ('UL', LegalEntity.EntityTypes.BC_ULC_COMPANY.value, RequestActions.AML.value),
            ('UC', LegalEntity.EntityTypes.BC_ULC_COMPANY.value, RequestActions.CNV.value),
            ('CUL', LegalEntity.EntityTypes.BC_ULC_COMPANY.value, RequestActions.CHG.value),
            ('ULCT', LegalEntity.EntityTypes.BC_ULC_COMPANY.value, RequestActions.MVE.value),
            ('RUL', LegalEntity.EntityTypes.BC_ULC_COMPANY.value, RequestActions.REST.value),
            ('RUL', LegalEntity.EntityTypes.BC_ULC_COMPANY.value, RequestActions.REH.value),
            ('RUL', LegalEntity.EntityTypes.BC_ULC_COMPANY.value, RequestActions.REN.value),
            # ('UA', LegalEntity.EntityTypes.XPRO_UNLIMITED_LIABILITY_COMPANY.value, RequestActions.AS.value),
            # ('XUL', LegalEntity.EntityTypes.XPRO_UNLIMITED_LIABILITY_COMPANY.value, RequestActions.NEW_AML.value),
            # ('XUL', LegalEntity.EntityTypes.XPRO_UNLIMITED_LIABILITY_COMPANY.value, RequestActions.NEW.value),
            # ('XUL', LegalEntity.EntityTypes.XPRO_UNLIMITED_LIABILITY_COMPANY.value, RequestActions.AML.value),
            # ('XCUL', LegalEntity.EntityTypes.XPRO_UNLIMITED_LIABILITY_COMPANY.value, RequestActions.CHG.value),
            # ('XRUL', LegalEntity.EntityTypes.XPRO_UNLIMITED_LIABILITY_COMPANY.value, RequestActions.REST.value),
            # ('XRUL', LegalEntity.EntityTypes.XPRO_UNLIMITED_LIABILITY_COMPANY.value, RequestActions.REH.value),
            # ('XRUL', LegalEntity.EntityTypes.XPRO_UNLIMITED_LIABILITY_COMPANY.value, RequestActions.REN.value),
            ('FI', LegalEntity.EntityTypes.FINANCIAL.value, RequestActions.NEW.value),
            ('CFI', LegalEntity.EntityTypes.FINANCIAL.value, RequestActions.CHG.value),
            ('RFI', LegalEntity.EntityTypes.FINANCIAL.value, RequestActions.REST.value),
            ('RFI', LegalEntity.EntityTypes.FINANCIAL.value, RequestActions.REH.value),
            ('RFI', LegalEntity.EntityTypes.FINANCIAL.value, RequestActions.REN.value),
            ('PA', LegalEntity.EntityTypes.PRIVATE_ACT.value, RequestActions.NEW.value),
            ('PAR', LegalEntity.EntityTypes.PARISHES.value, RequestActions.NEW.value),
            ('BC', LegalEntity.EntityTypes.BCOMP.value, RequestActions.NEW.value),
            ('BEAM', LegalEntity.EntityTypes.BCOMP.value, RequestActions.AML.value),
            ('BEC', LegalEntity.EntityTypes.BCOMP.value, RequestActions.CHG.value),
            ('BECT', LegalEntity.EntityTypes.BCOMP.value, RequestActions.MVE.value),
            ('BERE', LegalEntity.EntityTypes.BCOMP.value, RequestActions.REST.value),
            ('BERE', LegalEntity.EntityTypes.BCOMP.value, RequestActions.REH.value),
            ('BERE', LegalEntity.EntityTypes.BCOMP.value, RequestActions.REN.value),
            ('BECV', LegalEntity.EntityTypes.BCOMP.value, RequestActions.CNV.value),
            ('BECR', LegalEntity.EntityTypes.COMP.value, RequestActions.CNV.value)
        ]

        rv = []

        # get list of matching items
        for item in request_type_mapping:
            match0 = (not nr_type_cd) or (item[0] == nr_type_cd)
            match1 = (not entity_type_cd) or (item[1] == entity_type_cd)
            match2 = (not request_action_cd) or (item[2] == request_action_cd)

            if match0 and match1 and match2:
                rv.append({
                    'nrTypeCd': item[0],
                    'entityTypeCd': item[1],
                    'requestActionCd': item[2]
                })

        if not rv:
            return {'message': 'no mappings found'}, HTTPStatus.NOT_FOUND

        return rv, HTTPStatus.OK
