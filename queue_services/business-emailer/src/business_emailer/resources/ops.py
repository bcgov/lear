from http import HTTPStatus

from flask import Blueprint
from business_emailer.services import logger




bp = Blueprint("ops", __name__)


@bp.route("healthz", methods=("GET",))
async def get_healthz():
    """Return a JSON object stating the health of the Service and dependencies."""
    return {'message': 'api is healthy'}, HTTPStatus.OK


@bp.route("readyz", methods=("GET",))
async def get():
    """Return a JSON object that identifies if the service is setupAnd ready to work."""
    return {'message': 'api is ready'}, HTTPStatus.OK
