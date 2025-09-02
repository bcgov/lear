import base64
import json
import random
from http import HTTPStatus
from threading import Thread
from queue import Queue

from flask import Flask, request
from gcp_queue import GcpQueue
from google.cloud import pubsub_v1
from testcontainers.google import PubSubContainer
from testcontainers.core.waiting_utils import wait_for_logs

import pytest
from simple_cloudevent import SimpleCloudEvent, to_queue_message

CLOUD_EVENT = SimpleCloudEvent(
    id="fake-id",
    source="fake-for-tests",
    subject="fake-subject",
    type="payment",
    data={
        "paymentToken": {
            "id": "29590",
            "statusCode": "COMPLETED",
            "filingIdentifier": 12345,
            "corpTypeCode": "BC",
        }
    },
)
#
# This needs to mimic the envelope created by GCP PubSb when call a resource
#
CLOUD_EVENT_ENVELOPE = {
    "subscription": "projects/PUBSUB_PROJECT_ID/subscriptions/SUBSCRIPTION_ID",
    "message": {
        "data": base64.b64encode(to_queue_message(CLOUD_EVENT)).decode("UTF-8"),
        "messageId": "10",
        "attributes": {},
    },
    "id": 1,
}


def create_app(queue: Queue):
    app = Flask(__name__)
    default_config = {}
    app.config.from_object(default_config)
    queue.init_app(app)
    return app


def setup_pubsub(pubsub: PubSubContainer, endpoint: str):
    # Create a new topic
    publisher = pubsub.get_publisher_client()
    topic_path = publisher.topic_path(pubsub.project, "my-topic")
    publisher.create_topic(name=topic_path)

    # Create a subscription
    push_config = pubsub_v1.types.PushConfig(push_endpoint=endpoint)
    subscriber = pubsub.get_subscriber_client()
    subscription_path = subscriber.subscription_path(pubsub.project, "my-subscription")
    subscriber.create_subscription(
        request={
            "name": subscription_path,
            "topic": topic_path,
            "push_config": push_config,
        },
    )

    
    # Create a subscription - github (linux) version
    push_config = pubsub_v1.types.PushConfig(push_endpoint=endpoint.replace("host.docker.internal", "172.17.0.1"))
    subscription_path = subscriber.subscription_path(pubsub.project, "my-subscription-github")
    subscriber.create_subscription(
        request={
            "name": subscription_path,
            "topic": topic_path,
            "push_config": push_config,
        },
    )
    return publisher, topic_path


def run_thread(app: Flask, port: int):
    thread = Thread(
        target=app.run, daemon=True, kwargs=dict(host="localhost", port=port)
    )
    thread.start()


class MockRequest:
    def __init__(self, data):
        self.data = data

    def get_json(self):
        return json.loads(self.data.decode())

import socket

@pytest.fixture(scope='function')
def get_free_port():
    sock = socket.socket()
    sock.bind(('', 0))
    port = sock.getsockname()[1]
    yield port
    sock.close()

def push_listener(get_free_port, gcp_queue, msg_queue):
    subdirectory = "/"
    # port = 9898
    port = get_free_port
    host = "host.docker.internal"
    endpoint = f"http://{host}:{str(port)}{subdirectory}"
    app = create_app(queue=gcp_queue)

    @app.route("/", methods=["POST"])
    def message():
        msg_queue.put(MockRequest(request.data))
        return {}, 201

    run_thread(app, port)
    return endpoint

@pytest.fixture(scope='function')
def pubsub():
    with PubSubContainer() as pubsub:
        wait_for_logs(pubsub, r"Server started, listening on \d+", timeout=10)
        yield pubsub


def test_queue_cloud_event(get_free_port, pubsub):

    gcp_queue = GcpQueue()
    queue = Queue()
    endpoint = push_listener(get_free_port, gcp_queue, queue)
    publisher, topic_path = setup_pubsub(pubsub, endpoint)

    # Publish a message
    test_message = to_queue_message(CLOUD_EVENT)
    publisher.publish(topic_path, test_message)

    msg = queue.get()
    ce = gcp_queue.get_simple_cloud_event(msg, wrapped=True)

    assert ce.data == CLOUD_EVENT.data
