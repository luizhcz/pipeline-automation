from contextlib import contextmanager
from enum import Enum
import json
import time
from typing import Any, Callable, Dict, Optional, Protocol

import pika
from pydantic import Field
from pydantic_settings import BaseSettings

from utils.logger import get_logger

logger = get_logger(__name__)

# ---------------------------------------------------------------------------

class _Settings(BaseSettings):
    rabbitmq_url: str = Field(..., env="RABBITMQ_URL")
    task_queue: str   = Field("ipynb_tasks",      env="TASK_QUEUE")
    dlq_queue: str    = Field("ipynb_tasks_dlq",  env="DLQ_QUEUE")

    class Config:
        env_file = ".env"

_settings = _Settings()


class QueueName(str, Enum):
    TASK = _settings.task_queue
    DLQ  = _settings.dlq_queue


# ---------------------------------------------------------------------------
# Conexão genérica -----------------------------------------------------------
# ---------------------------------------------------------------------------

class _Connection:
    """Wrapper de connection-with-reconnect.

    `confirm=True` habilita *publisher confirms*.
    """

    def __init__(self, url: str, confirm: bool):
        self._params   = pika.URLParameters(url)
        self._confirm  = confirm
        self._conn:    Optional[pika.BlockingConnection] = None
        self._channel: Optional[pika.adapters.blocking_connection.BlockingChannel] = None

    # -------------- helpers -----------------

    def _connect(self) -> None:
        delay = 1
        while True:
            try:
                self._conn    = pika.BlockingConnection(self._params)
                self._channel = self._conn.channel()
                if self._confirm:
                    self._channel.confirm_delivery()
                logger.info("RabbitMQ connected (confirm=%s)", self._confirm)
                return
            except pika.exceptions.AMQPConnectionError as exc:
                logger.warning("RabbitMQ connection failed (%s); retrying in %ss…", exc, delay)
                time.sleep(delay)
                delay = min(delay * 2, 30)

    @property
    def channel(self):
        if not self._channel or self._channel.is_closed:
            self._connect()
        return self._channel

    def close(self) -> None:
        if self._conn and not self._conn.is_closed:
            self._conn.close()

    # permite usar `with _Connection(...) as ch:`
    def __enter__(self):
        return self.channel

    def __exit__(self, *_):
        self.close()


# ---------------------------------------------------------------------------
# Interface (protocol) -------------------------------------------------------
# ---------------------------------------------------------------------------

class MessageBroker(Protocol):
    def publish(self, message: Dict[str, Any], queue: QueueName = QueueName.TASK) -> None: ...
    def consume(
        self,
        callback: Callable[[Dict[str, Any]], bool],
        queue: QueueName = QueueName.TASK,
    ) -> None: ...


# ---------------------------------------------------------------------------
# Publisher Broker -----------------------------------------------------------
# ---------------------------------------------------------------------------

class PublisherRabbitMQBroker(MessageBroker):
    """Broker usado pela API (producer) e, ocasionalmente, pelo worker para reenfileirar."""

    def __init__(self, conn: _Connection | None = None):
        # confirm_delivery=True garante *publisher confirms*
        self._conn = conn or _Connection(_settings.rabbitmq_url, confirm=True)

    # ------------- publish --------------------

    def publish(self, message: Dict[str, Any], queue: QueueName = QueueName.TASK) -> None:
        with self._conn as ch:
            ch.queue_declare(queue=queue.value, durable=True)
            ch.basic_publish(
                "",
                routing_key=queue.value,
                body=json.dumps(message).encode(),
                properties=pika.BasicProperties(delivery_mode=2),  # persisted
            )
            logger.debug("Published to %s", queue.value)

    # ------------- consume (não usado pelo producer) --------
    def consume(self, *_, **__):  # noqa: D401
        raise NotImplementedError("Use ConsumerRabbitMQBroker para consumir.")


# ---------------------------------------------------------------------------
# Consumer Broker -----------------------------------------------------------
# ---------------------------------------------------------------------------

class ConsumerRabbitMQBroker(MessageBroker):
    """Broker exclusivo do Worker para *consumir*."""

    def __init__(self, conn: _Connection | None = None):
        # confirm_delivery=False → evita fechar canal em nack
        self._conn = conn or _Connection(_settings.rabbitmq_url, confirm=False)

    # ---------- publish (re-uso interno) ------
    def publish(self, message: Dict[str, Any], queue: QueueName = QueueName.TASK) -> None:
        PublisherRabbitMQBroker(self._conn).publish(message, queue)

    # ---------- consume -----------------------
    def consume(
        self,
        callback: Callable[[Dict[str, Any]], bool],
        queue: QueueName = QueueName.TASK,
    ) -> None:
        ch = self._conn.channel
        ch.queue_declare(queue=queue.value, durable=True)
        ch.basic_qos(prefetch_count=1)

        def _on_msg(channel, method, _props, body: bytes):
            payload = json.loads(body)
            ok = False
            try:
                ok = callback(payload)  # True = ACK, False = NACK requeue
            except Exception as exc:     # noqa: BLE001
                logger.error("Erro inesperado no callback: %s", exc)

            if ok:
                if channel.is_open:
                    channel.basic_ack(method.delivery_tag)
            else:
                logger.warning("Task falhou; requeue=True")
                if channel.is_open:
                    channel.basic_nack(method.delivery_tag, requeue=True)

        ch.basic_consume(queue=queue.value, on_message_callback=_on_msg)
        logger.info("Consuming queue '%s'…", queue.value)

        try:
            ch.start_consuming()
        except KeyboardInterrupt:
            logger.info("Consumer interrompido (Ctrl+C)")
            ch.stop_consuming()
            self._conn.close()


# ---------------------------------------------------------------------------
# Alias de compatibilidade ---------------------------------------------------
# ---------------------------------------------------------------------------

class RabbitMQBroker(PublisherRabbitMQBroker):
    """Alias mantido apenas para evitar alterações em pontos que importam
    `RabbitMQBroker` diretamente.
    """
    pass