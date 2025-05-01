import json
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Dict, List, Optional

import pyodbc

from config.settings import settings
from utils.logger import get_logger

logger = get_logger(__name__)

# ---------------------------------------------------------------------------
# Modelo
# ---------------------------------------------------------------------------
@dataclass(slots=True)
class NotebookRow:
    name: str
    version: str
    file_path: Path
    required_params: List[str]
    output_ext: str

    def to_dict(self) -> Dict:
        d = asdict(self)
        d["file_path"] = str(self.file_path)
        return d


# ---------------------------------------------------------------------------
# Conexão
# ---------------------------------------------------------------------------
def _conn():
    return pyodbc.connect(settings.sql_server_connection_string, autocommit=False)


# ---------------------------------------------------------------------------
# Repositório
# ---------------------------------------------------------------------------
class NotebookRepository:
    TABLE = "Notebook"

    # --------------  CREATE ------------------
    def insert(
        self,
        name: str,
        version: str,
        file_path: Path,
        required_params: List[str],
        output_ext: str,
    ) -> None:
        with _conn() as c:
            c.cursor().execute(
                f"INSERT INTO {self.TABLE} "
                "(NotebookName, Version, FilePath, RequiredParams, OutputExt) "
                "VALUES (?, ?, ?, ?, ?)",
                name,
                version,
                str(file_path),
                json.dumps(required_params),
                output_ext,
            )
        logger.info("Notebook %s v%s registrado", name, version)

    # --------------  READ --------------------
    def fetch(
        self, name: str, version: str | None = None
    ) -> Optional[Dict[str, NotebookRow] | NotebookRow]:
        with _conn() as c:
            cur = c.cursor()
            if version:
                cur.execute(
                    f"SELECT * FROM {self.TABLE} WHERE NotebookName=? AND Version=?",
                    name,
                    version,
                )
                row = cur.fetchone()
                if not row:
                    return None
                return self._row_to_obj(row)

            # all versions for notebook
            cur.execute(f"SELECT * FROM {self.TABLE} WHERE NotebookName=?", name)
            rows = cur.fetchall()
            if not rows:
                return None
            return {r.Version: self._row_to_obj(r) for r in rows}

    def list_all(self) -> List[NotebookRow]:
        with _conn() as c:
            cur = c.cursor()
            cur.execute(f"SELECT * FROM {self.TABLE}")
            return [self._row_to_obj(r) for r in cur.fetchall()]

    # --------------  UPDATE ------------------
    def update(
        self,
        name: str,
        version: str,
        file_path: Path | None = None,
        required_params: List[str] | None = None,
        output_ext: str | None = None,
    ) -> bool:
        sets, vals = [], []
        if file_path is not None:
            sets.append("FilePath=?")
            vals.append(str(file_path))
        if required_params is not None:
            sets.append("RequiredParams=?")
            vals.append(json.dumps(required_params))
        if output_ext is not None:
            sets.append("OutputExt=?")
            vals.append(output_ext)

        if not sets:  # nothing to update
            return False

        vals += [name, version]
        with _conn() as c:
            cur = c.cursor()
            cur.execute(
                f"UPDATE {self.TABLE} SET {', '.join(sets)} "
                "WHERE NotebookName=? AND Version=?",
                *vals,
            )
            updated = cur.rowcount
        return updated > 0

    # -------- util interno -----------
    @staticmethod
    def _row_to_obj(r) -> NotebookRow:
        return NotebookRow(
            name=r.NotebookName,
            version=r.Version,
            file_path=Path(r.FilePath),
            required_params=json.loads(r.RequiredParams),
            output_ext=r.OutputExt,
        )
