import signal
import threading
import time
from contextlib import contextmanager
from typing import Dict

from infrastructure.broker.rabbitmq import (
    ConsumerRabbitMQBroker,
    MessageBroker,
    PublisherRabbitMQBroker,
    QueueName,
)
from infrastructure.persistence.sqlserver import (
    RequestRepository,
    SqlServerRequestRepository,
)
from services.notebook_runner import NotebookRunner, NotebookRunError
from config.settings import settings
from utils.logger import get_logger

logger = get_logger(__name__)

# ---------------------------------------------------------------------------
# Soft-timeout util ----------------------------------------------------------
# ---------------------------------------------------------------------------


@contextmanager
def soft_timeout(seconds: int):
    """Levanta TimeoutError depois de *seconds* em Unix e Windows."""
    if hasattr(signal, "SIGALRM"):  # Unix
        def _handler(_sig, _frame):
            raise TimeoutError("Tempo limite excedido")

        signal.signal(signal.SIGALRM, _handler)
        signal.alarm(seconds)
        try:
            yield
        finally:
            signal.alarm(0)
    else:  # Windows
        timer = threading.Timer(seconds, lambda: (_ for _ in ()).throw(TimeoutError()))
        timer.start()
        try:
            yield
        finally:
            timer.cancel()


# ---------------------------------------------------------------------------
# Worker --------------------------------------------------------------------
# ---------------------------------------------------------------------------


class TaskWorker:
    def __init__(
        self,
        broker: MessageBroker | None = None,
        repo: RequestRepository | None = None,
        runner: NotebookRunner | None = None,
        max_retries: int | None = None,
    ):
        self._broker = broker or ConsumerRabbitMQBroker()
        self._publisher = PublisherRabbitMQBroker()

        self._repo = repo or SqlServerRequestRepository()
        self._runner = runner or NotebookRunner()
        self._max_retries = 2 

    # ------------------------------------------------------------------

    def _process(self, msg: Dict) -> bool:
        """Callback que processa a task.
        Retorna True → ACK
        Retorna False → NACK (requeue=True)
        """
        req_id = msg["request_id"]
        nb     = msg["notebook_name"]
        ver    = msg.get("version")
        params = msg.get("params", {})

        logger.debug("Processando request %s – %s", req_id, nb)

        try:
            self._repo.mark_started(req_id)
            with soft_timeout(settings.notebook_timeout + 30):
                otype, opath = self._runner.execute(req_id, nb, ver, params)

            self._repo.mark_success(req_id, otype, str(opath))
            logger.info("Request %s concluída com sucesso", req_id)
            return True

        except (NotebookRunError, TimeoutError, Exception) as exc:  # noqa: BLE001
            logger.error("Request %s falhou: %s", req_id, exc)

            # ---------- RETRY / DLQ -----------------
            self._repo.inc_retry(req_id)
            retry = self._repo.current_retry(req_id)

            if retry <= self._max_retries:
                backoff = 2 ** retry
                logger.warning(
                    "Retry %s/%s em %ss – reenfileirando",
                    retry,
                    self._max_retries,
                    backoff,
                )
                time.sleep(backoff)
                msg["retry"] = retry
                self._publisher.publish(msg)     # re-enfileira cópia modificada
                return True                      # ACK → remove original
            else:
                logger.error("Request %s excedeu max_retries → DLQ", req_id)
                self._repo.mark_failure(req_id, str(exc))
                self._publisher.publish(msg, queue=QueueName.DLQ)
                return True                      # ACK → remove original

    # ------------------------------------------------------------------

    def start(self) -> None:
        logger.info("Worker iniciado – Ctrl+C para sair")

        def _graceful(_sig, _frame):
            raise KeyboardInterrupt

        for sig in (signal.SIGINT, signal.SIGTERM):
            signal.signal(sig, _graceful)

        try:
            self._broker.consume(self._process)
        except KeyboardInterrupt:
            logger.info("Worker encerrado")


# ---------------------------------------------------------------------------

def main() -> None:
    TaskWorker().start()


if __name__ == "__main__":
    main()
