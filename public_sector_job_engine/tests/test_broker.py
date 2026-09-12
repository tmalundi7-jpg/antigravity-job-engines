import time
import pytest
from core.messaging import MessageBroker

def test_broker_pub_sub():
    broker = MessageBroker()
    test_queue = "unit_test_queue"
    broker.declare_queue(test_queue)

    received_messages = []

    def callback(msg):
        received_messages.append(msg)

    # Start consumer in background
    broker.consume(test_queue, callback, block=False)

    payload = {"test_key": "test_value"}
    broker.publish(
        queue_name=test_queue,
        payload=payload,
        source="test_runner",
        target="tester",
        msg_type="test_event"
    )

    time.sleep(0.3)
    assert len(received_messages) == 1
    assert received_messages[0]["payload"]["test_key"] == "test_value"
    assert received_messages[0]["source_agent"] == "test_runner"
