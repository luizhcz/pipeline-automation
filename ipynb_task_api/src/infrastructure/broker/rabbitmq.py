import asyncio
import json
from enum import Enum
from typing import Any, Awaitable, Callable, Dict

import aio_pika
from aio_pika import exceptions as aio_exc
from config.settings import settings
from utils.logger import get_logger

logger = get_logger(__name__)


# --------------------------------------------------------------------- #
# 1 ▪ Enum com os nomes das filas                                       #
# --------------------------------------------------------------------- #
class QueueName(str, Enum):
    TASK: str = settings.task_queue
    DLQ:  str = settings.dlq_queue


# --------------------------------------------------------------------- #
# 2 ▪ Conexão e canais                                                  #
# --------------------------------------------------------------------- #
class _AsyncConnection:
    """Mantém uma única RobustConnection viva para toda a aplicação."""

    def __init__(self, url: str, heartbeat: int = 60) -> None:
        self._url        = url
        self._heartbeat  = heartbeat
        self._conn: aio_pika.RobustConnection | None = None
        self._pub_ch: aio_pika.RobustChannel  | None = None
        self._lock       = asyncio.Lock()

    # ---------- helpers ------------------------------------------------- #
    async def _new_conn(self) -> aio_pika.RobustConnection:
        while True:
            try:
                logger.info("RabbitMQ → conectando (async)…")
                conn = await aio_pika.connect_robust(
                    self._url,
                    heartbeat=self._heartbeat,
                    # reconexão exponencial automática
                )
                logger.info("RabbitMQ conectado ✔")
                return conn
            except aio_exc.AMQPConnectionError as err:
                logger.warning("Falha na conexão (%s) – tentando novamente…", err)
                await asyncio.sleep(2)   # back-off fixo; `connect_robust` já usa exponencial

    async def conn(self) -> aio_pika.RobustConnection:
        async with self._lock:
            if not self._conn or self._conn.is_closed:
                self._conn = await self._new_conn()
        return self._conn

    # ---------- canal publisher ----------------------------------------- #
    async def pub_channel(self) -> aio_pika.RobustChannel:
        if self._pub_ch and not self._pub_ch.is_closed:
            return self._pub_ch

        ch = await (await self.conn()).channel(publisher_confirms=True)
        await ch.set_qos(prefetch_count=0)   # publisher não prefetch
        self._pub_ch = ch
        return ch

    # ---------- canal consumer ------------------------------------------ #
    async def new_consumer_channel(self, prefetch: int) -> aio_pika.RobustChannel:
        ch = await (await self.conn()).channel()
        await ch.set_qos(prefetch_count=prefetch)
        return ch

    async def close(self) -> None:
        if self._conn and not self._conn.is_closed:
            await self._conn.close()


# --------------------------------------------------------------------- #
# 3 ▪ Publisher                                                         #
# --------------------------------------------------------------------- #
class AsyncPublisher:
    def __init__(self, conn: _AsyncConnection | None = None):
        self._conn = conn or _AsyncConnection(settings.rabbitmq_url)

    async def _declare_queues(self) -> None:
        ch = await self._conn.pub_channel()
        # DLQ
        await ch.declare_queue(
            QueueName.DLQ.value, durable=True,
            arguments={"x-dead-letter-exchange": ""},
        )
        # Fila principal
        await ch.declare_queue(
            QueueName.TASK.value, durable=True,
            arguments={"x-dead-letter-exchange": ""},
        )

    async def publish(self, message: Dict[str, Any],
                      queue: QueueName = QueueName.TASK) -> None:
        await self._declare_queues()              # executado só na 1ª vez
        ch   = await self._conn.pub_channel()
        body = aio_pika.Message(
            body=json.dumps(message).encode(),
            delivery_mode=aio_pika.DeliveryMode.PERSISTENT,
        )

        try:
            await ch.default_exchange.publish(
                body, routing_key=queue.value, mandatory=True
            )
            logger.debug("Mensagem publicada em %s", queue.value)
        except aio_exc.UnroutableError:
            logger.error("Mensagem não roteada – descartada")
        except aio_exc.AMQPError:
            logger.exception("Erro no publish – canal será recriado")
            # canal será recriado na próxima chamada


# --------------------------------------------------------------------- #
# 4 ▪ Consumer                                                          #
# --------------------------------------------------------------------- #
class AsyncConsumer:
    """Consome TASK, manda rejeições para DLQ.  
    `callback` deve retornar *True* se a task foi processada com sucesso."""

    def __init__(
        self,
        conn: _AsyncConnection | None = None,
        prefetch: int = 1,
    ):
        self._conn = conn or _AsyncConnection(settings.rabbitmq_url)
        self._prefetch = prefetch

    async def consume(
        self,
        callback: Callable[[Dict[str, Any]], Awaitable[bool]],
        queue: QueueName = QueueName.TASK,
    ) -> None:
        ch = await self._conn.new_consumer_channel(self._prefetch)

        # declara fila (idempotente)
        q = await ch.declare_queue(
            queue.value,
            durable=True,
            arguments={"x-dead-letter-exchange": ""},
        )

        async with q.iterator() as it:
            logger.info("Consumindo fila '%s' (async)…", queue.value)

            async for msg in it:                        # type: aio_pika.IncomingMessage
                async with msg.process(requeue=False):  # ack automático se não lançar
                    try:
                        payload = json.loads(msg.body)
                    except json.JSONDecodeError:
                        logger.exception("JSON inválido – DLQ")
                        await msg.reject(requeue=False)
                        continue

                    try:
                        ok = await callback(payload)
                    except Exception:
                        logger.exception("Erro inesperado no callback")
                        ok = False

                    if not ok:
                        logger.warning("Task falhou – DLQ")
                        await msg.reject(requeue=False)
                    # se ok==True, o context manager já envia ACK