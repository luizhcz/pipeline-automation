import time
from pathlib import Path
from typing import Any, Dict, Tuple

import papermill as pm
from nbclient.exceptions import CellExecutionError

from infrastructure.persistence.notebook_repository import NotebookRepository
from utils.logger import get_logger
from config.settings import settings

logger = get_logger(__name__)


class OutputType(str):
    JSON = "json"
    XML = "xml"
    EXCEL = "excel"

    @classmethod
    def from_extension(cls, ext: str) -> "OutputType":
        mapping = {".json": cls.JSON, ".xml": cls.XML, ".xlsx": cls.EXCEL}
        if ext.lower() not in mapping:
            raise ValueError(f"Extensão {ext} não suportada")
        return mapping[ext.lower()]


class NotebookRunError(RuntimeError):
    """Erro alto-nível na execução do notebook."""


class NotebookRunner:
    """Executa notebooks parametrizados via Papermill."""

    def __init__(
        self,
        timeout: int | None = None,
        kernel_name: str | None = None,
    ):
        self._timeout = timeout or settings.notebook_timeout
        self._kernel_name = kernel_name or "python3"
        self._repo = NotebookRepository()

    # ------------------------------------------------------------------

    def execute(
        self,
        request_id: str,
        nb_name: str,
        version: str | None,
        params: Dict[str, Any],
    ) -> Tuple[OutputType, Path]:
        rows = self._repo.fetch(nb_name)
        if not rows:
            raise NotebookRunError(f"Notebook '{nb_name}' não cadastrado")

        row = rows.get(version) if version else rows[max(rows, key=lambda v: int(v))]

        nb_path: Path = settings.notebook_base / row.file_path
        out_dir = settings.output_base / request_id
        out_dir.mkdir(parents=True, exist_ok=True)

        exec_nb = out_dir / f"executed_{nb_path.stem}.ipynb"
        target = out_dir / f"{request_id}{row.output_ext}"
        injected = {**params, "output_filename": str(target)}

        logger.info("Executando %s v%s", nb_name, row.version)
        start = time.perf_counter()
        try:
            pm.execute_notebook(
                str(nb_path),
                str(exec_nb),
                parameters=injected,
                timeout=self._timeout,
                kernel_name=self._kernel_name,
            )
        except CellExecutionError as exc:
            raise NotebookRunError(str(exc)) from exc
        finally:
            logger.info("Notebook %s finalizado em %.1f s", nb_name, time.perf_counter() - start)

        if not target.exists():
            raise NotebookRunError("Arquivo de saída não foi gerado")

        return OutputType.from_extension(target.suffix), target