from contextlib import contextmanager
from dataclasses import dataclass
from datetime import datetime
from enum import Enum
import json
from typing import Any, Dict, Optional

import pyodbc

from config.settings import settings
from utils.logger import get_logger

logger = get_logger(__name__)

# ---------------------------------------------------------------------------

class TaskStatus(str, Enum):
    PENDING = "PENDING"
    STARTED = "STARTED"
    SUCCESS = "SUCCESS"
    FAILURE = "FAILURE"


@dataclass(slots=True)
class TaskRecord:
    request_id: str
    notebook_name: str
    version: str | None
    params: Dict[str, Any]
    status: TaskStatus
    retry_count: int
    created_at: datetime
    started_at: Optional[datetime]
    finished_at: Optional[datetime]
    output_type: Optional[str]
    output_path: Optional[str]
    error: Optional[str]

# ---------------------------------------------------------------------------

@contextmanager
def _connection():
    conn = pyodbc.connect(settings.sql_server_connection_string, autocommit=False)
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()

# ---------------------------------------------------------------------------

class RequestRepository: ...


class SqlServerRequestRepository(RequestRepository):
    TABLE = "Tasks"
    _DDL = f"""
    IF NOT EXISTS (SELECT * FROM sysobjects WHERE name='{TABLE}' AND xtype='U')
    BEGIN
        CREATE TABLE {TABLE} (
            RequestId UNIQUEIDENTIFIER PRIMARY KEY,
            NotebookName NVARCHAR(200),
            Version NVARCHAR(10) NULL,
            Params NVARCHAR(MAX),
            Status NVARCHAR(30),
            RetryCount INT DEFAULT 0,
            CreatedAt DATETIME DEFAULT GETDATE(),
            StartedAt DATETIME NULL,
            FinishedAt DATETIME NULL,
            OutputType NVARCHAR(10) NULL,
            OutputPath NVARCHAR(4000) NULL,
            Error NVARCHAR(MAX) NULL
        );
    END;


    IF NOT EXISTS (SELECT * FROM sysobjects WHERE name='Notebook' AND xtype='U')
    BEGIN
        CREATE TABLE Notebook (
            NotebookName NVARCHAR(200) NOT NULL,
            Version      NVARCHAR(10)  NOT NULL,
            FilePath     NVARCHAR(4000) NOT NULL,
            RequiredParams NVARCHAR(MAX) NOT NULL,    -- JSON: ["year", "branch"]
            OutputExt    NVARCHAR(10)  NOT NULL,      -- ".json" | ".xml" | ".xlsx"
            CONSTRAINT PK_Notebook PRIMARY KEY (NotebookName, Version)
        );
    END;
    """

    def __init__(self, ensure_schema: bool = True) -> None:
        if ensure_schema:
            with _connection() as conn:
                conn.cursor().execute(self._DDL)

    # ------------- helpers -----------------------

    @staticmethod
    def _row_to_record(row) -> TaskRecord:
        return TaskRecord(
            request_id=row.RequestId,
            notebook_name=row.NotebookName,
            version=row.Version,
            params=json.loads(row.Params or "{}"),
            status=TaskStatus(row.Status),
            retry_count=row.RetryCount,
            created_at=row.CreatedAt,
            started_at=row.StartedAt,
            finished_at=row.FinishedAt,
            output_type=row.OutputType,
            output_path=row.OutputPath,
            error=row.Error,
        )

    # ------------- CRUD --------------------------

    def insert_new_request(
        self, request_id: str, nb: str, ver: str | None, params: Dict[str, Any]
    ) -> None:
        with _connection() as conn:
            conn.cursor().execute(
                f"INSERT INTO {self.TABLE} "
                "(RequestId, NotebookName, Version, Params, Status) "
                "VALUES (?, ?, ?, ?, ?)",
                request_id,
                nb,
                ver,
                json.dumps(params, ensure_ascii=False),
                TaskStatus.PENDING.value,
            )

    def inc_retry(self, request_id: str) -> None:
        with _connection() as conn:
            conn.cursor().execute(
                f"UPDATE {self.TABLE} SET RetryCount = RetryCount + 1 WHERE RequestId=?",
                request_id,
            )

    def current_retry(self, request_id: str) -> int:
        with _connection() as conn:
            cur = conn.cursor()
            cur.execute(f"SELECT RetryCount FROM {self.TABLE} WHERE RequestId=?", request_id)
            return cur.fetchval() or 0

    def mark_started(self, request_id: str) -> None:
        with _connection() as conn:
            conn.cursor().execute(
                f"UPDATE {self.TABLE} SET Status=?, StartedAt=GETDATE() WHERE RequestId=?",
                TaskStatus.STARTED.value,
                request_id,
            )

    def mark_success(self, request_id: str, otype: str, opath: str) -> None:
        with _connection() as conn:
            conn.cursor().execute(
                f"UPDATE {self.TABLE} SET Status=?, FinishedAt=GETDATE(), "
                "OutputType=?, OutputPath=? WHERE RequestId=?",
                TaskStatus.SUCCESS.value,
                otype,
                opath,
                request_id,
            )

    def mark_failure(self, request_id: str, error: str) -> None:
        with _connection() as conn:
            conn.cursor().execute(
                f"UPDATE {self.TABLE} SET Status=?, FinishedAt=GETDATE(), Error=? "
                "WHERE RequestId=?",
                TaskStatus.FAILURE.value,
                error,
                request_id,
            )

    def fetch_task(self, request_id: str) -> Optional[TaskRecord]:
        with _connection() as conn:
            cur = conn.cursor()
            cur.execute(f"SELECT * FROM {self.TABLE} WHERE RequestId=?", request_id)
            row = cur.fetchone()
            return self._row_to_record(row) if row else None