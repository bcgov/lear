from queue import Queue

from gcp_queue import GcpQueue

from .conftest import push_listener, setup_pubsub, CLOUD_EVENT, to_queue_message


def test_queue_cloud_event(get_free_port, pubsub):

    gcp_queue = GcpQueue()
    queue = Queue()
    endpoint = push_listener(get_free_port, gcp_queue, queue)
    publisher, topic_path = setup_pubsub(pubsub, endpoint)

    # Publish a message
    test_message = to_queue_message(CLOUD_EVENT)
    publisher.publish(topic_path, test_message)

    msg = queue.get(block=False)
    ce = gcp_queue.get_simple_cloud_event(msg, wrapped=True)

    assert ce.data == CLOUD_EVENT.data
