import asyncio
import signal
from typing import Any, Dict

from infrastructure.broker.rabbitmq import (
    AsyncConsumer,
    AsyncPublisher,
    QueueName,
    _AsyncConnection,
)
from infrastructure.persistence.sqlserver import (
    RequestRepository,
    SqlServerRequestRepository,
)
from services.notebook_runner import NotebookRunner, NotebookRunError
from config.settings import settings
from utils.logger import get_logger

logger = get_logger(__name__)


class TaskWorkerAsync:
    """Worker que consome a fila **TASK** de forma assíncrona."""

    def __init__(
        self,
        conn: _AsyncConnection | None = None,
        repo: RequestRepository | None = None,
        runner: NotebookRunner | None = None,
        max_retries: int | None = None,
        prefetch: int = 1,
    ) -> None:
        self._conn = conn or _AsyncConnection(settings.rabbitmq_url)
        self._consumer = AsyncConsumer(self._conn, prefetch=prefetch)
        self._publisher = AsyncPublisher(self._conn)

        self._repo: RequestRepository = repo or SqlServerRequestRepository()
        self._runner: NotebookRunner = runner or NotebookRunner()
        self._max_retries: int = max_retries or 2

    # ----------------------------------------------------------
    # helpers
    # ----------------------------------------------------------

    async def _run_notebook(self, *args, **kwargs):
        """Executa `NotebookRunner.execute` em *thread pool*."""
        return await asyncio.to_thread(self._runner.execute, *args, **kwargs)

    async def _repo_call(self, fn, *args, **kwargs):
        """Executa métodos do repositório no pool de *threads*."""
        return await asyncio.to_thread(fn, *args, **kwargs)

    # ----------------------------------------------------------
    # callback de consumo
    # ----------------------------------------------------------

    async def _process(self, msg: Dict[str, Any]) -> bool:
        """Processa uma mensagem.

        Retorna **True** → ACK
        Retorna **False** → NACK (mas nunca requeue: DLQ)
        """
        req_id = msg["request_id"]
        nb = msg["notebook_name"]
        ver = msg.get("version")
        params = msg.get("params", {})

        logger.debug("Processando request %s – %s", req_id, nb)

        try:
            await self._repo_call(self._repo.mark_started, req_id)

            timeout = settings.notebook_timeout + 30
            otype, opath = await asyncio.wait_for(
                self._run_notebook(req_id, nb, ver, params),
                timeout=timeout,
            )

            await self._repo_call(self._repo.mark_success, req_id, otype, str(opath))
            logger.info("Request %s concluída com sucesso", req_id)
            return True

        except (NotebookRunError, asyncio.TimeoutError, Exception) as exc:  # noqa: BLE001
            logger.error("Request %s falhou: %s", req_id, exc)

            await self._repo_call(self._repo.inc_retry, req_id)
            retry = await self._repo_call(self._repo.current_retry, req_id)

            if retry <= self._max_retries:
                backoff = 2 ** retry
                logger.warning(
                    "Retry %s/%s em %ss – reenfileirando",
                    retry,
                    self._max_retries,
                    backoff,
                )
                await asyncio.sleep(backoff)
                msg["retry"] = retry
                await self._publisher.publish(msg)
                return True  # ACK → remove original
            else:
                logger.error("Request %s excedeu max_retries → DLQ", req_id)
                await self._repo_call(self._repo.mark_failure, req_id, str(exc))
                await self._publisher.publish(msg, queue=QueueName.DLQ)
                return True  # ACK → remove original

    # ----------------------------------------------------------
    # ciclo de vida
    # ----------------------------------------------------------

    async def start(self) -> None:
        """Inicia o loop de consumo e lida com SIGINT/SIGTERM."""
        loop = asyncio.get_running_loop()
        stop_event = asyncio.Event()

        def _graceful() -> None:
            logger.info("Sinal recebido – encerrando…")
            stop_event.set()

        for sig in (signal.SIGINT, signal.SIGTERM):
            try:
                loop.add_signal_handler(sig, _graceful)
            except NotImplementedError:  # Windows SIGTERM
                signal.signal(sig, lambda *_: _graceful())

        consumer_task = asyncio.create_task(self._consumer.consume(self._process))

        await stop_event.wait()  # aguarda Ctrl+C ou kill
        consumer_task.cancel()
        try:
            await consumer_task
        except asyncio.CancelledError:
            pass

        await self._conn.close()
        logger.info("Worker encerrado")


# -------------------------------------------------------------------------
# CLI helper
# -------------------------------------------------------------------------

def main() -> None:
    asyncio.run(TaskWorkerAsync().start())


if __name__ == "__main__":
    main()