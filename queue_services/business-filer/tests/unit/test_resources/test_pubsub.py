import base64
import json
from threading import Thread
from queue import Queue

from flask import Flask, request
from google.cloud import pubsub_v1
from testcontainers.google import PubSubContainer
from testcontainers.core.waiting_utils import wait_for_logs

def test_pubsub_container():
    """Assert that the TestContainer and PubSub spins up correctly."""
    with PubSubContainer() as pubsub:
        wait_for_logs(pubsub, r"Server started, listening on \d+", timeout=10)
        # Create a new topic
        publisher = pubsub.get_publisher_client()
        topic_path = publisher.topic_path(pubsub.project, "my-topic")
        publisher.create_topic(name=topic_path)

        # Create a subscription
        subscriber = pubsub.get_subscriber_client()
        subscription_path = subscriber.subscription_path(
            pubsub.project, "my-subscription"
        )
        subscriber.create_subscription(
            request={"name": subscription_path, "topic": topic_path}
        )

        # Publish a message
        publisher.publish(topic_path, b"Hello world!")

        # Receive the message
        queue = Queue()
        subscriber.subscribe(subscription_path, queue.put)
        message = queue.get(timeout=1)
        assert message.data == b"Hello world!"
        message.ack()
