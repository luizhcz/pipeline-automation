from infrastructure.persistence.notebook_repository import NotebookRepository
from utils.logger import get_logger

logger = get_logger(__name__)


class TaskValidationError(ValueError):
    """Erro de domínio lançado quando a task não é válida."""


class NotebookValidator:
    """Valida nome, versão e parâmetros de uma task."""

    def __init__(self, repo: NotebookRepository | None = None) -> None:
        self._repo = repo or NotebookRepository()

    # ------------------------------------------------------------------

    def validate(
        self,
        notebook_name: str,
        version: str | None,
        params: dict,
    ):
        """Valida e devolve o NotebookRow se ok, caso contrário dispara erro."""
        rows = self._repo.fetch(notebook_name)
        if not rows:
            raise TaskValidationError(f"Notebook '{notebook_name}' não cadastrado")

        # versão (usa a mais alta se não especificada)
        ver = version or max(rows, key=lambda v: int(v))
        if ver not in rows:
            raise TaskValidationError(f"Versão {ver} não existe para '{notebook_name}'")

        row = rows[ver]

        missing = [p for p in row.required_params if p not in params]
        if missing:
            raise TaskValidationError(
                f"Parâmetros ausentes para '{notebook_name}': {', '.join(missing)}"
            )

        logger.debug("Notebook %s v%s validado", notebook_name, ver)
        return row  # retorna NotebookRow