import json
from dataclasses import dataclass, asdict
from datetime import datetime
from typing import List, Optional
from uuid import UUID

import pyodbc
from config.settings import settings
from utils.logger import get_logger

logger = get_logger(__name__)

@dataclass(slots=True)
class PipelineParameterRow:
    id: UUID
    pipeline_id: UUID
    name: str
    type: str
    value: Optional[str] = None  # armazenado como string (JSON, texto ou null)


@dataclass(slots=True)
class PipelineRow:
    id: UUID
    name: str
    description: Optional[str]
    created_at: datetime
    params: List[PipelineParameterRow]

def _conn():
    return pyodbc.connect(settings.sql_server_connection_string, autocommit=False)


class PipelineRepository:
    PIPELINE_TABLE = "Pipelines"
    PARAM_TABLE = "PipelineParameters"

    def fetch(self, pipeline_id: UUID) -> Optional[PipelineRow]:
        with _conn() as c:
            cur = c.cursor()

            # Buscar pipeline
            cur.execute(
                f"SELECT Id, Name, Description, CreatedAt FROM {self.PIPELINE_TABLE} WHERE Id = ?",
                str(pipeline_id),
            )
            row = cur.fetchone()
            if not row:
                return None

            # Buscar parâmetros
            cur.execute(
                f"SELECT Id, PipelineId, Name, Type, Value FROM {self.PARAM_TABLE} WHERE PipelineId = ?",
                str(pipeline_id),
            )
            param_rows = cur.fetchall()
            params = [self._param_row_to_obj(r) for r in param_rows]

            return PipelineRow(
                id=row.Id,
                name=row.Name,
                description=row.Description,
                created_at=row.CreatedAt,
                params=params,
            )

    def insert(self, pipeline: PipelineRow) -> None:
        with _conn() as c:
            cur = c.cursor()

            # Inserir Pipeline
            cur.execute(
                f"INSERT INTO {self.PIPELINE_TABLE} (Id, Name, Description, CreatedAt) VALUES (?, ?, ?, ?)",
                str(pipeline.id),
                pipeline.name,
                pipeline.description,
                pipeline.created_at,
            )

            # Inserir Parâmetros
            for p in pipeline.params:
                cur.execute(
                    f"INSERT INTO {self.PARAM_TABLE} (Id, PipelineId, Name, Type, Value) VALUES (?, ?, ?, ?, ?)",
                    str(p.id),
                    str(pipeline.id),
                    p.name,
                    p.type,
                    p.value,
                )

            logger.info("Pipeline %s registrado com %d parâmetros.", pipeline.name, len(pipeline.params))
    
    def list_all(self) -> List[PipelineRow]:
        with _conn() as c:
            cur = c.cursor()

            # Buscar todos os pipelines
            cur.execute(f"SELECT Id, Name, Description, CreatedAt FROM {self.PIPELINE_TABLE}")
            pipeline_rows = cur.fetchall()

            pipelines = []
            for p in pipeline_rows:
                # Buscar parâmetros de cada pipeline
                cur.execute(
                    f"SELECT Id, PipelineId, Name, Type, Value FROM {self.PARAM_TABLE} WHERE PipelineId = ?",
                    str(p.Id),
                )
                param_rows = cur.fetchall()
                params = [self._param_row_to_obj(r) for r in param_rows]

                pipelines.append(
                    PipelineRow(
                        id=p.Id,
                        name=p.Name,
                        description=p.Description,
                        created_at=p.CreatedAt,
                        params=params,
                    )
                )
            return pipelines
        
    def update(self, pipeline: PipelineRow) -> bool:
        with _conn() as c:
            cur = c.cursor()

            # Atualizar pipeline
            cur.execute(
                f"UPDATE {self.PIPELINE_TABLE} SET Name=?, Description=?, CreatedAt=? WHERE Id=?",
                pipeline.name,
                pipeline.description,
                pipeline.created_at,
                str(pipeline.id),
            )

            # Apagar parâmetros existentes
            cur.execute(
                f"DELETE FROM {self.PARAM_TABLE} WHERE PipelineId=?",
                str(pipeline.id),
            )

            # Inserir novos parâmetros
            for p in pipeline.params:
                cur.execute(
                    f"INSERT INTO {self.PARAM_TABLE} (Id, PipelineId, Name, Type, Value) VALUES (?, ?, ?, ?, ?)",
                    str(p.id),
                    str(pipeline.id),
                    p.name,
                    p.type,
                    p.value,
                )

            logger.info("Pipeline %s atualizado com %d parâmetros.", pipeline.name, len(pipeline.params))
            return True

    @staticmethod
    def _param_row_to_obj(r) -> PipelineParameterRow:
        return PipelineParameterRow(
            id=r.Id,
            pipeline_id=r.PipelineId,
            name=r.Name,
            type=r.Type,
            value=r.Value,
        )
