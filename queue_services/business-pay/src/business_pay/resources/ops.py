from contextlib import suppress
from http import HTTPStatus

from flask import Blueprint
from flask import current_app
from structured_logging import StructuredLogging

from business_pay.services import nats_queue


logger = StructuredLogging.get_logger()

bp = Blueprint("ops", __name__)


@bp.route("healthz", methods=("GET",))
async def get_healthz():
    """Return a JSON object stating the health of the Service and dependencies."""
    try:
        await nats_queue.connect()
        if not await nats_queue.is_healthy \
        or nats_queue.error_count >= current_app.config.get('NATS_CONNECT_ERROR_COUNT_MAX', 5):
            logger.debug('Connection is unhealthy, error_count: %s', nats_queue.error_count)
            return {'message': 'nats connection unhealthy'}, HTTPStatus.SERVICE_UNAVAILABLE

    except Exception as err:
        return {'message': 'nats connection unhealthy: ' + err}, HTTPStatus.SERVICE_UNAVAILABLE

    # reset
    logger.debug('helthy, resetting error_count')
    nats_queue._error_count = 0
    return {'message': 'api is healthy'}, HTTPStatus.OK


@bp.route("readyz", methods=("GET",))
async def get():
    """Return a JSON object that identifies if the service is setupAnd ready to work."""
    with suppress(Exception):
        await nats_queue.connect()

    return {'message': 'api is ready'}, HTTPStatus.OK
