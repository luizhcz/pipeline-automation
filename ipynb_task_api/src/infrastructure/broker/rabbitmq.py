"""
infrastructure/broker/rabbitmq.py
=================================

Wrapper de alto nível para RabbitMQ usando Pika **1.3.2**.

Principais características
--------------------------
* Conexão única, thread-safe, com reconexão exponencial
* Canais separados para publisher e consumer
* Publisher Confirms reais (`confirm_delivery()` + `wait_for_confirms()`)
* Fila principal + DLQ declaradas uma única vez
* Prefetch configurável
* Tratamento de JSON inválido e logging com stack-trace
"""

from __future__ import annotations

import json
import threading
import time
from enum import Enum
from typing import Any, Callable, Dict, Optional, Protocol
from urllib.parse import urlparse

import pika
from pika import exceptions as pk_exc

from config.settings import settings
from utils.logger import get_logger

logger = get_logger(__name__)


# --------------------------------------------------------------------------- #
# 1 ▪ Enum com os nomes das filas                                             #
# --------------------------------------------------------------------------- #
class QueueName(str, Enum):
    TASK = settings.task_queue
    DLQ = settings.dlq_queue


# --------------------------------------------------------------------------- #
# 2 ▪ Conexão persistente e thread-safe                                       #
# --------------------------------------------------------------------------- #
class _Connection:
    """Mantém uma única BlockingConnection viva e segura para múltiplas threads."""

    def __init__(self, url: str, heartbeat: int = 60, blocked_timeout: int = 30):
        self._params = pika.URLParameters(url)
        self._params.heartbeat = heartbeat
        self._params.blocked_connection_timeout = blocked_timeout

        self._conn: Optional[pika.BlockingConnection] = None
        self._lock = threading.Lock()

    # ------------- helpers -------------------------------------------------- #
    def _connect(self) -> pika.BlockingConnection:
        delay = 1
        parsed = urlparse(self._params.host)
        logger.info("RabbitMQ → conectando em %s:%s…", parsed.hostname, self._params.port)

        while True:
            try:
                conn = pika.BlockingConnection(self._params)
                logger.info("RabbitMQ conectado ✔")
                return conn
            except pk_exc.AMQPConnectionError as err:
                logger.warning("Falha na conexão (%s); tentando novamente em %ss…", err, delay)
                time.sleep(delay)
                delay = min(delay * 2, 30)

    @property
    def conn(self) -> pika.BlockingConnection:
        with self._lock:
            if not self._conn or self._conn.is_closed:
                self._conn = self._connect()
            return self._conn

    # ------------- canal ---------------------------------------------------- #
    def open_channel(
        self,
        confirms: bool = False,
    ) -> pika.adapters.blocking_connection.BlockingChannel:
        """
        Abre *novo* canal (não compartilha entre threads).

        Se ``confirms=True``, ativa publisher confirms usando a API do Pika 1.3.2:
        * ``channel.confirm_delivery()``
        * ``channel.wait_for_confirms()``
        """
        ch = self.conn.channel()

        if confirms:
            ch.confirm_delivery()
            ch._supports_wait = True  # flag interna para publish()

        return ch

    # ------------- encerramento -------------------------------------------- #
    def close(self) -> None:
        with self._lock:
            if self._conn and not self._conn.is_closed:
                self._conn.close()


# --------------------------------------------------------------------------- #
# 3 ▪ Interface de broker                                                     #
# --------------------------------------------------------------------------- #
class MessageBroker(Protocol):
    def publish(self, message: Dict[str, Any], queue: QueueName = QueueName.TASK) -> None: ...
    def consume(
        self,
        callback: Callable[[Dict[str, Any]], bool],
        queue: QueueName = QueueName.TASK,
    ) -> None: ...


# --------------------------------------------------------------------------- #
# 4 ▪ Publisher (API / re-enqueue)                                            #
# --------------------------------------------------------------------------- #
class PublisherRabbitMQBroker(MessageBroker):
    """Broker usado pela API para publicar mensagens (e pelo worker para reenfileirar)."""

    def __init__(self, conn: _Connection | None = None):
        self._conn = conn or _Connection(settings.rabbitmq_url)
        self._channel = self._conn.open_channel(confirms=True)
        self._declare_queues()

    def _declare_queues(self) -> None:
        """
        Declara fila principal e DLQ.  
        Se a fila já existir, faz `queue_declare(passive=True)` para
        evitar erro de inequivalent arg.
        """
        # 1. DLQ sempre pode ser declarada (ou reusada idempotentemente).
        self._channel.queue_declare(queue=QueueName.DLQ.value, durable=True)

        # 2. Verifica se a fila principal existe
        try:
            self._channel.queue_declare(queue=QueueName.TASK.value, passive=True)
            logger.info("Fila %s já existe – mantendo configuração atual.", QueueName.TASK.value)
        except pk_exc.ChannelClosedByBroker as err:
            if err.reply_code == 404:            # não existe → criar com DLX
                self._channel = self._conn.open_channel(confirms=True)  # canal novo
                args = {"x-dead-letter-exchange": ""}
                self._channel.queue_declare(
                    queue=QueueName.TASK.value,
                    durable=True,
                    arguments=args,
                )
                logger.info("Fila %s criada com DLX.", QueueName.TASK.value)
            else:
                raise  # outros erros continuam sendo propagados


    # ---------------- publish ------------------------------------------------ #
    def publish(self, message: Dict[str, Any], queue: QueueName = QueueName.TASK) -> None:
        body = json.dumps(message).encode()

        while True:
            try:
                self._channel.basic_publish(
                    exchange="",
                    routing_key=queue.value,
                    body=body,
                    mandatory=True,
                    properties=pika.BasicProperties(delivery_mode=2),
                )

                # aguarda confirmação do broker (ACK/NACK)
                if getattr(self._channel, "_supports_wait", False):
                    self._channel.wait_for_confirms()

                logger.debug("Mensagem publicada em %s", queue.value)
                return

            except (pk_exc.UnroutableError, pk_exc.NackError):
                logger.error("Mensagem NACK/Unroutable – descartada: %s", message)
                return
            except pk_exc.ChannelClosedByBroker as err:
                logger.warning("Canal fechado (%s) – reabrindo…", err)
                self._channel = self._conn.open_channel(confirms=True)
            except pk_exc.AMQPError:
                logger.exception("Erro ao publicar; reabrindo canal…")
                self._channel = self._conn.open_channel(confirms=True)

    def consume(self, *_, **__):
        raise NotImplementedError("Publisher não consome mensagens.")


# --------------------------------------------------------------------------- #
# 5 ▪ Consumer (worker)                                                       #
# --------------------------------------------------------------------------- #
class ConsumerRabbitMQBroker(MessageBroker):
    """Broker exclusivo do worker para consumir mensagens."""

    def __init__(self, conn: _Connection | None = None, prefetch_count: int = 1):
        self._conn = conn or _Connection(settings.rabbitmq_url)
        self._channel = self._conn.open_channel()
        self._channel.queue_declare(queue=QueueName.TASK.value, durable=True)
        self._channel.basic_qos(prefetch_count=prefetch_count)

    # ---------------- republish -------------------------------------------- #
    def publish(self, message: Dict[str, Any], queue: QueueName = QueueName.TASK) -> None:
        # usa canal *exclusivo* de publisher para não interferir no consumer
        PublisherRabbitMQBroker(self._conn).publish(message, queue)

    # ---------------- consume ---------------------------------------------- #
    def consume(
        self,
        callback: Callable[[Dict[str, Any]], bool],
        queue: QueueName = QueueName.TASK,
    ) -> None:
        def _on_msg(ch, method, _props, body: bytes):
            try:
                payload = json.loads(body)
            except json.JSONDecodeError:
                logger.exception("JSON inválido – reject")
                ch.basic_reject(method.delivery_tag, requeue=False)
                return

            ok = False
            try:
                ok = callback(payload)  # True → ACK; False → DLQ
            except Exception:
                logger.exception("Erro inesperado no callback")

            if ok:
                ch.basic_ack(method.delivery_tag)
            else:
                logger.warning("Task falhou – DLQ")
                ch.basic_reject(method.delivery_tag, requeue=False)

        self._channel.basic_consume(queue=queue.value, on_message_callback=_on_msg)
        logger.info("Consumindo fila '%s'…", queue.value)

        try:
            self._channel.start_consuming()
        except KeyboardInterrupt:
            logger.info("Consumer interrompido (Ctrl+C)")
            self._channel.stop_consuming()
        finally:
            self._conn.close()


# --------------------------------------------------------------------------- #
# 6 ▪ Alias legado (mantido para não quebrar importações antigas)             #
# --------------------------------------------------------------------------- #
class RabbitMQBroker(PublisherRabbitMQBroker):
    """Mantém retrocompatibilidade com `RabbitMQBroker`."""
    ...