from __future__ import annotations

import json
import pathlib
import uuid
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional

from fastapi import Depends, FastAPI, HTTPException, Path as FPath
from fastapi.responses import FileResponse, JSONResponse
from pydantic import BaseModel, Field

from infrastructure.broker.rabbitmq import RabbitMQBroker
from infrastructure.persistence.sqlserver import (
    RequestRepository,
    SqlServerRequestRepository,
)
from infrastructure.persistence.notebook_repository import NotebookRepository
from services.validation.notebook_validator import NotebookValidator
from utils.logger import get_logger
from utils.ratelimiter import RateLimitMiddleware

logger = get_logger(__name__)

# ---------------------------------------------------------------------------
# DTOs
# ---------------------------------------------------------------------------
class OutputType(str, Enum):
    JSON = "json"
    EXCEL = "excel"
    XML = "xml"


class TaskRequestDTO(BaseModel):
    notebook_name: str
    version: Optional[str] = None
    params: Dict[str, Any]


class SubmitPayload(BaseModel):
    tasks: List[TaskRequestDTO]


class NotebookRegistrationDTO(BaseModel):
    notebook_name: str
    version: str
    file_path: str
    required_params: List[str]
    output_ext: str = Field(..., pattern=r"\.(json|xml|xlsx)$")


class NotebookUpdateDTO(BaseModel):
    file_path: Optional[Path] = None
    required_params: Optional[List[str]] = None
    output_ext: Optional[str] = Field(None, pattern=r"\.(json|xml|xlsx)$")


# ---------------------------------------------------------------------------
# Dependências
# ---------------------------------------------------------------------------
def get_repo() -> RequestRepository:
    return SqlServerRequestRepository()


def get_broker() -> RabbitMQBroker:
    return RabbitMQBroker()


def get_validator() -> NotebookValidator:
    return NotebookValidator()


def get_notebook_repo():
    return NotebookRepository()


# ---------------------------------------------------------------------------
# APP
# ---------------------------------------------------------------------------
app = FastAPI(title="ipynb Task API – v2.2")
#app.add_middleware(RateLimitMiddleware, max_calls=60, period=60)


# -------------------- SUBMIT ------------------------------
@app.post("/submit", status_code=204)
async def submit_tasks(
    payload: SubmitPayload,
    repo: RequestRepository = Depends(get_repo),
    broker: RabbitMQBroker = Depends(get_broker),
    validator: NotebookValidator = Depends(get_validator),
):
    req_ids: list[str] = []
    for t in payload.tasks:
        validator.validate(t.notebook_name, t.version, t.params)
        rid = str(uuid.uuid4())
        repo.insert_new_request(rid, t.notebook_name, t.version, t.params)
        broker.publish(
            {
                "request_id": rid,
                "notebook_name": t.notebook_name,
                "version": t.version,
                "params": t.params,
                "retry": 0,
            }
        )
        req_ids.append(rid)
    return {"request_ids": req_ids, "message": "Enfileirado"}


# -------------------- STATUS ------------------------------
@app.get("/status/{request_id}")
async def status(
    request_id: str = FPath(..., min_length=1),
    repo: RequestRepository = Depends(get_repo),
):
    rec = repo.fetch_task(request_id)
    if not rec:
        raise HTTPException(404, "Request não encontrado")
    return {
        "status": rec.status,
        "retry_count": rec.retry_count,
        "output_type": rec.output_type,
        "error": rec.error,
    }


# -------------------- RESULT ------------------------------
@app.get("/result/{request_id}")
async def result(
    request_id: str = FPath(..., min_length=1),
    repo: RequestRepository = Depends(get_repo),
):
    rec = repo.fetch_task(request_id)
    if not rec:
        raise HTTPException(404, "Request não encontrado")
    if rec.status != "SUCCESS":
        raise HTTPException(409, "Tarefa ainda não concluída")
    path = pathlib.Path(rec.output_path)
    if not path.exists():
        raise HTTPException(500, "Arquivo não encontrado")
    otype = OutputType(rec.output_type)
    if otype is OutputType.JSON:
        with path.open(encoding="utf-8") as fp:
            return JSONResponse(json.load(fp))
    media = (
        "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        if otype is OutputType.EXCEL
        else "application/xml"
    )
    return FileResponse(str(path), media_type=media, filename=path.name)


# -------------------- NOTEBOOK CRUD -----------------------
@app.post("/notebooks", status_code=201)
async def register_notebook(
    dto: NotebookRegistrationDTO,
    repo: NotebookRepository = Depends(get_notebook_repo),
):
    rows = repo.fetch(dto.notebook_name)
    if rows and dto.version in rows:
        raise HTTPException(409, "Notebook + versão já cadastrados")
    repo.insert(
        dto.notebook_name,
        dto.version,
        dto.file_path,
        dto.required_params,
        dto.output_ext,
    )
    return {"detail": "Notebook registrado"}


@app.get("/notebooks")
async def list_notebooks(repo: NotebookRepository = Depends(get_notebook_repo)):
    rows = repo.list_all()
    return [r.to_dict() for r in rows]


@app.get("/notebooks/{notebook_name}")
async def list_versions(
    notebook_name: str,
    repo: NotebookRepository = Depends(get_notebook_repo),
):
    rows = repo.fetch(notebook_name)
    if rows is None:
        raise HTTPException(404, "Notebook não encontrado")
    return [r.to_dict() for r in rows.values()]


@app.get("/notebooks/{notebook_name}/{version}")
async def notebook_detail(
    notebook_name: str,
    version: str,
    repo: NotebookRepository = Depends(get_notebook_repo),
):
    row = repo.fetch(notebook_name, version)
    if row is None:
        raise HTTPException(404, "Notebook/version não encontrado")
    return row.to_dict()


@app.put("/notebooks/{notebook_name}/{version}", status_code=204)
async def update_notebook(
    notebook_name: str,
    version: str,
    dto: NotebookUpdateDTO,
    repo: NotebookRepository = Depends(get_notebook_repo),
):
    if not any([dto.file_path, dto.required_params, dto.output_ext]):
        raise HTTPException(400, "Nada para atualizar")

    updated = repo.update(
        notebook_name,
        version,
        file_path=dto.file_path,
        required_params=dto.required_params,
        output_ext=dto.output_ext,
    )
    if not updated:
        raise HTTPException(404, "Notebook/version não encontrado")
    return JSONResponse(status_code=204, content=None)