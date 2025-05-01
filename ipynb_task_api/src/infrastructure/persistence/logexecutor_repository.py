from dataclasses import dataclass
from datetime import datetime
from uuid import UUID, uuid4
from typing import List

import pyodbc
from config.settings import settings
from utils.logger import get_logger

logger = get_logger(__name__)


@dataclass(slots=True)
class LogRow:
    mensagem: str
    data: datetime
    request_id: UUID | None = None  # novo campo opcional


class LogsExecutorRepository:
    LOG_TABLE = "LogsExecutor"

    def __init__(self):
        self.conn_string = settings.sql_server_connection_string

    def _conn(self):
        return pyodbc.connect(self.conn_string, autocommit=False)

    def insert_log(self, mensagem: str, request_id: UUID | None = None) -> UUID:
        data_atual = datetime.utcnow()

        with self._conn() as c:
            cur = c.cursor()
            cur.execute(
                f"INSERT INTO {self.LOG_TABLE} (RequestId, Mensagem, Data) VALUES (?, ?, ?)",
                str(request_id),
                mensagem,
                data_atual,
            )
            logger.info("Log registrado: %s", mensagem)
        return request_id
