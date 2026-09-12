import time
import uuid
import threading
from concurrent.futures import ThreadPoolExecutor
import pytest
from core.messaging import LocalMessageBroker, MessageBroker


def test_broker_high_concurrency_pub_sub():
    """
    Stress test: 10 concurrent producer threads publishing 100 messages each
    (1,000 total messages) to LocalMessageBroker. Verify 100% arrival,
    zero message loss, and full payload integrity.
    """
    broker = MessageBroker()
    queue_name = f"stress_queue_{uuid.uuid4().hex[:8]}"
    broker.declare_queue(queue_name)

    received_messages = []
    lock = threading.Lock()

    def callback(msg):
        with lock:
            received_messages.append(msg)

    # Start consumer in background
    broker.consume(queue_name, callback, block=False)

    num_threads = 10
    messages_per_thread = 100
    total_expected = num_threads * messages_per_thread

    def producer(thread_idx):
        for msg_idx in range(messages_per_thread):
            broker.publish(
                queue_name=queue_name,
                payload={
                    "thread_id": thread_idx,
                    "seq": msg_idx,
                    "data": f"payload_{thread_idx}_{msg_idx}"
                },
                source=f"producer_{thread_idx}",
                target="stress_consumer",
                msg_type="stress_msg",
                correlation_id=f"corr_{thread_idx}"
            )

    start_time = time.time()
    with ThreadPoolExecutor(max_workers=num_threads) as executor:
        futures = [executor.submit(producer, t) for t in range(num_threads)]
        for f in futures:
            f.result()

    # Wait for consumer to process all messages
    timeout = 10.0
    while time.time() - start_time < timeout:
        with lock:
            if len(received_messages) >= total_expected:
                break
        time.sleep(0.1)

    with lock:
        count = len(received_messages)

    assert count == total_expected, f"Expected {total_expected} messages, received {count}"

    # Verify envelope integrity
    with lock:
        for msg in received_messages:
            assert "message_id" in msg and msg["message_id"]
            assert "correlation_id" in msg and msg["correlation_id"].startswith("corr_")
            assert "timestamp" in msg and msg["timestamp"]
            assert "source_agent" in msg and msg["source_agent"].startswith("producer_")
            assert msg["target_agent"] == "stress_consumer"
            assert msg["type"] == "stress_msg"
            assert "payload" in msg
            assert "thread_id" in msg["payload"]
            assert "seq" in msg["payload"]

    # Verify no duplicate messages (unique message_ids)
    with lock:
        message_ids = set(m["message_id"] for m in received_messages)
        assert len(message_ids) == total_expected, f"Duplicate message IDs found! {len(message_ids)} vs {total_expected}"


def test_broker_multi_queue_concurrency():
    """
    Verify concurrency across multiple independent queues simultaneously.
    """
    broker = MessageBroker()
    num_queues = 5
    msgs_per_queue = 50

    queues = [f"multi_q_{uuid.uuid4().hex[:6]}_{i}" for i in range(num_queues)]
    received = {q: [] for q in queues}
    lock = threading.Lock()

    for q in queues:
        def make_cb(q_name):
            def cb(msg):
                with lock:
                    received[q_name].append(msg)
            return cb
        broker.consume(q, make_cb(q), block=False)

    def publish_to_queue(q_name):
        for i in range(msgs_per_queue):
            broker.publish(
                queue_name=q_name,
                payload={"index": i, "queue": q_name},
                source="multi_tester",
                target=q_name,
                msg_type="multi_test"
            )

    with ThreadPoolExecutor(max_workers=num_queues) as pool:
        list(pool.map(publish_to_queue, queues))

    timeout = 8.0
    start = time.time()
    while time.time() - start < timeout:
        with lock:
            all_done = all(len(received[q]) >= msgs_per_queue for q in queues)
            if all_done:
                break
        time.sleep(0.1)

    with lock:
        for q in queues:
            assert len(received[q]) == msgs_per_queue, f"Queue {q} expected {msgs_per_queue}, got {len(received[q])}"


def test_broker_callback_exception_isolation():
    """
    Verify that an exception raised inside a consumer callback does not
    terminate the consumer thread or block subsequent messages on the queue.
    """
    broker = MessageBroker()
    queue_name = f"fault_queue_{uuid.uuid4().hex[:8]}"
    broker.declare_queue(queue_name)

    received = []
    lock = threading.Lock()

    def faulty_callback(msg):
        payload = msg.get("payload", {})
        if payload.get("should_fail"):
            raise ValueError("Intentional simulated error in consumer callback")
        with lock:
            received.append(msg)

    broker.consume(queue_name, faulty_callback, block=False)

    # Publish a normal message
    broker.publish(queue_name, {"msg_id": 1, "should_fail": False}, "tester", "target", "test")
    # Publish a message that raises an exception
    broker.publish(queue_name, {"msg_id": 2, "should_fail": True}, "tester", "target", "test")
    # Publish another normal message
    broker.publish(queue_name, {"msg_id": 3, "should_fail": False}, "tester", "target", "test")

    timeout = 3.0
    start = time.time()
    while time.time() - start < timeout:
        with lock:
            if len(received) >= 2:
                break
        time.sleep(0.1)

    with lock:
        assert len(received) == 2, f"Expected 2 successful messages processed, got {len(received)}"
        msg_ids = [m["payload"]["msg_id"] for m in received]
        assert 1 in msg_ids and 3 in msg_ids
