from http import HTTPStatus

from flask import Blueprint

from business_pay.services import nats_queue

bp = Blueprint("ops", __name__)


@bp.route("healthz", methods=("GET",))
async def get_healthz():
    """Return a JSON object stating the health of the Service and dependencies."""
    try:
        if not await nats_queue.is_healthy \
        or nats_queue.error_count >= 5:
            return {'message': 'nats connection unhealthy'}, HTTPStatus.SERVICE_UNAVAILABLE

    except Exception as err:
        return {'message': 'nats connection unhealthy: ' + err}, HTTPStatus.SERVICE_UNAVAILABLE

    return {'message': 'api is healthy'}, HTTPStatus.OK


@bp.route("readyz", methods=("GET",))
def get():
    """Return a JSON object that identifies if the service is setupAnd ready to work."""
    return {'message': 'api is ready'}, HTTPStatus.OK
