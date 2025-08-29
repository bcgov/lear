from queue import Queue

from flask import Flask
from gcp_queue import GcpQueue
from google.cloud import pubsub_v1
from testcontainers.google import PubSubContainer
from testcontainers.core.waiting_utils import wait_for_logs

def test_basic_pubsub():

    with PubSubContainer() as pubsub:
        wait_for_logs(pubsub, r"Server started, listening on \d+", timeout=10)

        msg = b"my test message"

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
        publisher.publish(topic_path, msg)

        # Receive the message
        queue = Queue()
        subscriber.subscribe(subscription_path, queue.put)
        message = queue.get(timeout=1)
        assert message.data == msg
        message.ack()


def create_app(queue: GcpQueue):
    app = Flask(__name__)
    default_config = {}
    app.config.from_object(default_config)
    queue.init_app(app)
    return app

def setup_topic(pubsub: PubSubContainer, endpoint: str):
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
    return publisher, topic_path


def test_gcp_queue():
    """Test sending a message via gcp_queue, in the Filer config.
    
    Just to ensure everything got installed and is workling correctly.
    """
    with PubSubContainer() as pubsub:
        wait_for_logs(pubsub, r"Server started, listening on \d+", timeout=10)

        #
        ## 1. Setup
        #
        msg = b"my test message"

        gcp_queue = GcpQueue()
        app = create_app(gcp_queue)

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

 
        #
        ## 2. Test Publish a message
        #
        try:
            gcp_queue._publisher = publisher
            gcp_queue.publish(topic_path, msg)
        except Exception as err:
            print(err)

        #
        ## 3. Verify Receive the message
        #
        queue = Queue()
        subscriber.subscribe(subscription_path, queue.put)
        message = queue.get(timeout=1)
        assert message.data == msg
        message.ack()
