import re
from pathlib import Path
from typing import Dict, List, Annotated

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings

# ------------------------------- helper -------------------------------

def _int_from_env(v: str | int) -> int:
    if isinstance(v, int):
        return v
    # remove tudo depois de um # ou espaço extra
    v = re.split(r'#', v, maxsplit=1)[0].strip()
    return int(v)

# ---------------------------------------------------------------------------

class NotebookMeta(BaseSettings):
    versions: Dict[str, Path]
    required_params: List[str]
    output_ext: str

    def latest_version(self) -> str:
        return max(self.versions, key=lambda v: int(v))

    def path_for(self, version: str | None = None) -> Path:
        v = version or self.latest_version()
        if v not in self.versions:
            raise ValueError(f"Version {v} not available")
        return self.versions[v]


class AppSettings(BaseSettings):
    sql_server_connection_string: str = Field(
        "DRIVER={ODBC Driver 17 for SQL Server};SERVER=localhost;"
        "DATABASE=TaskDB;Trusted_Connection=yes;",
        env="SQL_SERVER_CONNECTION_STRING",
    )
    rabbitmq_url: str = Field("amqp://guest:guest@localhost:5672/", env="RABBITMQ_URL")
    task_queue: str = Field("ipynb_tasks", env="TASK_QUEUE")
    dlq_queue: str = Field("ipynb_tasks_dlq", env="DLQ_QUEUE")
    max_retries: Annotated[int, Field(env="MAX_RETRIES")] = 3
    notebook_timeout: Annotated[int, Field(env="NOTEBOOK_TIMEOUT")] = 600

    base_dir: Path = Field(default_factory=lambda: Path(__file__).resolve().parent.parent.parent)

    @property
    def output_base(self) -> Path:
        p = self.base_dir / "outputs"
        p.mkdir(exist_ok=True)
        return p
    
    @property
    def notebook_base(self) -> Path:
        p = self.base_dir / "notebooks"
        p.mkdir(exist_ok=True)
        return p

    notebook_registry: Dict[str, NotebookMeta] = {}

    # ---------- validadores ------------
    @field_validator("max_retries", "notebook_timeout", mode="before")
    @classmethod
    def _parse_ints(cls, v):  # noqa: N805
        return _int_from_env(v)

    def _build_registry(cls, v, values):
        if v:
            return v
        b = values["base_dir"]
        return {
            "sales_report": NotebookMeta(
                versions={"1": b / "notebooks/sales_report_v1.ipynb"},
                required_params=["year"],
                output_ext=".json",
            ),
            "inventory_sync": NotebookMeta(
                versions={"1": b / "notebooks/inventory_sync_v1.ipynb"},
                required_params=["rows"],
                output_ext=".xlsx",
            ),
            "user_export": NotebookMeta(
                versions={"1": b / "notebooks/user_export_v1.ipynb"},
                required_params=["tag"],
                output_ext=".xml",
            ),
        }

    class Config:
        env_file = ".env"
        case_sensitive = False


settings = AppSettings()