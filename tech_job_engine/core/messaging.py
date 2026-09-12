import json
import uuid
import queue
import threading
import logging
import concurrent.futures
from datetime import datetime, timezone
import config

logger = logging.getLogger("core.messaging")


class LocalMessageBroker:
    _instance = None
    _class_lock = threading.Lock()

    def __new__(cls, *args, **kwargs):
        with cls._class_lock:
            if cls._instance is None:
                inst = super(LocalMessageBroker, cls).__new__(cls)
                inst._queues = {}
                inst._pools = {}
                inst._threads = []
                inst._thread_handles = {}   # queue_name -> (thread, pool)
                inst._running = True
                inst._rlock = threading.RLock()
                cls._instance = inst
            return cls._instance

    @classmethod
    def reset(cls):
        """Reset singleton state for test isolation."""
        with cls._class_lock:
            if cls._instance is not None:
                cls._instance._running = False
                for t in cls._instance._threads:
                    t.join(timeout=0.5)
                for pool in cls._instance._pools.values():
                    pool.shutdown(wait=False)
            cls._instance = None

    def declare_queue(self, queue_name: str):
        with self._rlock:
            if queue_name not in self._queues:
                self._queues[queue_name] = queue.Queue()
                logger.debug(f"[LocalBroker] Declared queue '{queue_name}'")

    def publish(self, queue_name: str, payload: dict, source: str, target: str, msg_type: str, correlation_id=None):
        if queue_name not in self._queues:
            self.declare_queue(queue_name)
        envelope = {
            "message_id": str(uuid.uuid4()),
            "correlation_id": correlation_id or str(uuid.uuid4()),
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "source_agent": source,
            "target_agent": target,
            "type": msg_type,
            "payload": payload
        }
        logger.debug(f"[LocalBroker] Publishing {msg_type} from {source} to {queue_name}")
        self._queues[queue_name].put(envelope)

    def consume(self, queue_name: str, callback, block: bool = True):
        self.declare_queue(queue_name)
        q = self._queues[queue_name]
        pool = concurrent.futures.ThreadPoolExecutor(
            max_workers=6, thread_name_prefix=f"Pool-{queue_name}"
        )
        with self._rlock:
            self._pools[queue_name] = pool

        def _worker():
            while self._running:
                try:
                    msg = q.get(timeout=0.5)

                    def _dispatch(m):
                        try:
                            callback(m)
                        except Exception as e:
                            logger.error(
                                f"[LocalBroker] Error in callback for {queue_name}: {e}",
                                exc_info=True,
                            )
                        finally:
                            q.task_done()

                    try:
                        pool.submit(_dispatch, msg)
                    except RuntimeError:
                        # Pool shut down; exit the worker loop cleanly
                        break
                except queue.Empty:
                    continue
            pool.shutdown(wait=False)

        if block:
            _worker()
        else:
            t = threading.Thread(target=_worker, daemon=True, name=f"Consumer-{queue_name}")
            t.start()
            with self._rlock:
                self._threads.append(t)
                self._thread_handles[queue_name] = (t, pool)
            logger.info(f"[LocalBroker] Started concurrent consumer on queue '{queue_name}'")

    def stop(self):
        self._running = False
        for t in self._threads:
            t.join(timeout=1.5)
        for pool in self._pools.values():
            pool.shutdown(wait=False)

    def __enter__(self):
        return self

    def __exit__(self, *args):
        self.stop()


class RabbitMQBroker:
    def __init__(self, uri: str):
        import pika
        self.pika = pika
        self.connection = pika.BlockingConnection(pika.URLParameters(uri))
        self.channel = self.connection.channel()
        logger.info(f"[RabbitMQ] Connected to {uri}")

    def declare_queue(self, queue_name: str):
        self.channel.queue_declare(queue=queue_name, durable=True)

    def publish(self, queue_name: str, payload: dict, source: str, target: str, msg_type: str, correlation_id=None):
        envelope = {
            "message_id": str(uuid.uuid4()),
            "correlation_id": correlation_id or str(uuid.uuid4()),
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "source_agent": source,
            "target_agent": target,
            "type": msg_type,
            "payload": payload
        }
        self.channel.basic_publish(
            exchange='',
            routing_key=queue_name,
            body=json.dumps(envelope),
            properties=self.pika.BasicProperties(
                delivery_mode=self.pika.spec.PERSISTENT_DELIVERY_MODE
            )
        )

    def consume(self, queue_name: str, callback, block: bool = True):
        def wrapper(ch, method, properties, body):
            msg = json.loads(body)
            try:
                callback(msg)
            finally:
                ch.basic_ack(delivery_tag=method.delivery_tag)

        self.channel.basic_consume(queue=queue_name, on_message_callback=wrapper)
        if block:
            self.channel.start_consuming()
        else:
            t = threading.Thread(target=self.channel.start_consuming, daemon=True)
            t.start()

    def stop(self):
        try:
            self.channel.stop_consuming()
            self.connection.close()
        except Exception:
            pass

    def __enter__(self):
        return self

    def __exit__(self, *args):
        self.stop()


def MessageBroker():
    """
    Factory: returns RabbitMQBroker when pika+RabbitMQ is reachable,
    otherwise returns the process-local LocalMessageBroker singleton.
    """
    uri = getattr(config, "RABBITMQ_URI", "")
    if uri:
        try:
            import pika
            return RabbitMQBroker(uri)
        except Exception as e:
            logger.info(f"RabbitMQ unavailable ({e}). Using in-process LocalMessageBroker.")
    return LocalMessageBroker()
