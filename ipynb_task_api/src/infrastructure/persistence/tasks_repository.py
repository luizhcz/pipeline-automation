from dataclasses import dataclass
from datetime import datetime
from uuid import UUID
from typing import List, Optional
import pyodbc

from config.settings import settings
from utils.logger import get_logger

logger = get_logger(__name__)


@dataclass(slots=True)
class LogRow:
    mensagem: str
    data: datetime


@dataclass(slots=True)
class TaskRow:
    request_id: UUID
    notebook_name: str
    version: str
    params: str
    status: str
    retry_count: int
    created_at: datetime
    started_at: Optional[datetime]
    finished_at: Optional[datetime]
    output_type: Optional[str]
    output_path: Optional[str]
    error: Optional[str]
    logs: Optional[List[LogRow]]


class TaskRepository:
    def __init__(self):
        self.conn_string = settings.sql_server_connection_string

    def _conn(self):
        return pyodbc.connect(self.conn_string, autocommit=False)

    def list_tasks_with_logs(self) -> List[TaskRow]:
        query = """
            WITH TopTasks AS (
                SELECT TOP 50 *
                FROM Celery.dbo.Tasks
                ORDER BY CreatedAt DESC
            )
            SELECT 
                T.RequestId,
                T.NotebookName,
                T.Version,
                T.Params,
                T.Status,
                T.RetryCount,
                T.CreatedAt,
                T.StartedAt,
                T.FinishedAt,
                T.OutputType,
                T.OutputPath,
                T.Error,
                L.Mensagem,
                L.Data
            FROM TopTasks T
            LEFT JOIN Celery.dbo.LogsExecutor L ON T.RequestId = L.RequestId
            ORDER BY T.CreatedAt DESC, L.Data ASC;
        """

        with self._conn() as c:
            cur = c.cursor()
            cur.execute(query)
            rows = cur.fetchall()

        tasks_dict = {}

        for row in rows:
            rid = row.RequestId
            if rid not in tasks_dict:
                tasks_dict[rid] = TaskRow(
                    request_id=rid,
                    notebook_name=row.NotebookName,
                    version=row.Version,
                    params=row.Params,
                    status=row.Status,
                    retry_count=row.RetryCount,
                    created_at=row.CreatedAt,
                    started_at=row.StartedAt,
                    finished_at=row.FinishedAt,
                    output_type=row.OutputType,
                    output_path=row.OutputPath,
                    error=row.Error,
                    logs=[],
                )

            if row.Mensagem is not None and row.Data is not None:
                tasks_dict[rid].logs.append(
                    LogRow(
                        mensagem=row.Mensagem,
                        data=row.Data,
                    )
                )

        return list(tasks_dict.values())
