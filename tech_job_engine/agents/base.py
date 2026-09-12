import logging
import traceback
import threading
from tenacity import retry, wait_exponential, stop_after_attempt
from core.messaging import MessageBroker

logger = logging.getLogger("agents.base")


class BaseAgent:
    def __init__(self, name: str, input_queue: str):
        self.name = name
        self.input_queue = input_queue
        self.broker = MessageBroker()
        self.broker.declare_queue(input_queue)
        self.broker.declare_queue("master_queue")
        self._processed_lock = threading.Lock()
        self.processed_messages = set()
        self._running = True

    # ── lifecycle ──────────────────────────────────────────────────────────────
    def run(self, block: bool = True):
        logger.info(f"[{self.name}] Listening on queue '{self.input_queue}' (block={block})")
        self.broker.consume(self.input_queue, self.handle_message, block=block)

    def stop(self):
        """Gracefully stop this agent."""
        self._running = False
        if hasattr(self.broker, "stop"):
            self.broker.stop()
        logger.info(f"[{self.name}] Stopped.")

    # context-manager support: `with SomeAgent() as agent: ...`
    def __enter__(self):
        return self

    def __exit__(self, *args):
        self.stop()

    # ── message handling ───────────────────────────────────────────────────────
    def handle_message(self, msg: dict):
        msg_id = msg.get("message_id")
        with self._processed_lock:
            if msg_id and msg_id in self.processed_messages:
                logger.info(f"[{self.name}] Duplicate message {msg_id} skipped (idempotent guard)")
                return

        try:
            self._process_with_retry(msg)
            if msg_id:
                with self._processed_lock:
                    self.processed_messages.add(msg_id)
        except Exception as e:
            logger.error(f"[{self.name}] Error processing message {msg_id}: {e}")
            traceback.print_exc()
            self.send_response(
                target="master_queue",
                payload={"error": str(e), "failed_message_id": msg_id},
                orig_msg=msg,
                msg_type="error",
            )

    @retry(
        wait=wait_exponential(multiplier=1, min=1, max=30),
        stop=stop_after_attempt(3),
        reraise=True,
    )
    def _process_with_retry(self, msg: dict):
        self.process_message(msg)

    def process_message(self, msg: dict):
        raise NotImplementedError

    def send_response(
        self,
        target: str,
        payload: dict,
        orig_msg: dict,
        msg_type: str = "task_response",
    ):
        self.broker.publish(
            queue_name=target,
            payload=payload,
            source=self.name,
            target=target,
            msg_type=msg_type,
            correlation_id=orig_msg.get("correlation_id"),
        )
