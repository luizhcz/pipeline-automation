import json
import pathlib
import uuid
from uuid import UUID
from datetime import datetime
from enum import Enum
from pathlib import Path

from dotenv import load_dotenv  # python-dotenv
load_dotenv(Path(__file__).resolve().parents[2] / ".env")  # carrega cedo

from typing import Any, Dict, List, Optional

from fastapi import Depends, FastAPI, HTTPException, Path as FPath
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from pydantic import BaseModel, Field

from infrastructure.broker.rabbitmq import RabbitMQBroker
from infrastructure.persistence.sqlserver import (
    RequestRepository,
    SqlServerRequestRepository,
)
from infrastructure.persistence.notebook_repository import NotebookRepository
from infrastructure.persistence.pipeline_repository import PipelineRepository, PipelineRow, PipelineParameterRow
from infrastructure.persistence.logexecutor_repository import LogsExecutorRepository
from infrastructure.persistence.tasks_repository import TaskRepository
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

class TaskLogDTO(BaseModel):
    mensagem: str
    data: datetime

class TaskDTO(BaseModel):
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
    logs: List[TaskLogDTO]

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

class PipelineParameterDTO(BaseModel):
    name: str
    type: str


class PipelineCreateDTO(BaseModel):
    name: str
    description: Optional[str]
    parameters: List[PipelineParameterDTO]


class PipelineUpdateDTO(BaseModel):
    name: Optional[str]
    description: Optional[str]
    parameters: Optional[List[PipelineParameterDTO]]

# ---------------------------------------------------------------------------
# Dependências
# ---------------------------------------------------------------------------
def get_repo() -> RequestRepository:
    return SqlServerRequestRepository()

def get_pipeline_repo():
    return PipelineRepository()

def get_broker() -> RabbitMQBroker:
    return RabbitMQBroker()


def get_validator() -> NotebookValidator:
    return NotebookValidator()

def get_task_repo():
    return TaskRepository()

def get_notebook_repo():
    return NotebookRepository()


# ---------------------------------------------------------------------------
# APP
# ---------------------------------------------------------------------------
app = FastAPI(title="ipynb Task API – v2.2")
#app.add_middleware(RateLimitMiddleware, max_calls=60, period=60)

origins = [
    "http://localhost:3000",         # React/Next dev
    # "https://meusite.com",         # produção
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,           # ou ["*"] em dev
    allow_credentials=True,          # se envia cookies/headers auth
    allow_methods=["*"],             # GET, POST, PUT, DELETE, …
    allow_headers=["*"],             # Content-Type, Authorization, …
    expose_headers=["Content-Disposition"],
)


# -------------------- SUBMIT ------------------------------
@app.post("/submit", status_code=201)
async def submit_tasks(
    payload: SubmitPayload,
    repo: RequestRepository = Depends(get_repo),
    broker: RabbitMQBroker = Depends(get_broker),
    validator: NotebookValidator = Depends(get_validator),
    logs_repo: LogsExecutorRepository = Depends(LogsExecutorRepository),
):
    req_id = uuid.uuid4()  # <- Identificador único da operação
    task_ids: list[str] = []

    try:
        logs_repo.insert_log("Iniciando submissão de tarefas", request_id=req_id)

        for task in payload.tasks:
            logs_repo.insert_log(
                f"Validando tarefa: notebook={task.notebook_name}, versão={task.version}",
                request_id=req_id
            )
            validator.validate(task.notebook_name, task.version, task.params)

            task_id = str(uuid.uuid4())
            logs_repo.insert_log(f"[INFO] Inserindo na fila", request_id=task_id)
            repo.insert_new_request(task_id, task.notebook_name, task.version, task.params)

            logs_repo.insert_log(f"[INFO] Publicando no broker", request_id=task_id)
            broker.publish({
                "request_id": task_id,
                "notebook_name": task.notebook_name,
                "version": task.version,
                "params": task.params,
                "retry": 0,
            })

            logs_repo.insert_log(f"[INFO] Tarefa publicada no broker", request_id=task_id)
            task_ids.append(task_id)

        logs_repo.insert_log(f"Todas tarefas enfileiradas com sucesso: total={len(task_ids)}", request_id=req_id)
        return {"request_ids": task_ids, "message": "Enfileirado"}

    except Exception as e:
        logs_repo.insert_log(f"Erro na submissão: {str(e)}", request_id=req_id)
        raise HTTPException(status_code=500, detail="Erro ao submeter as tarefas")

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
    finished_at = (
        rec.finished_at.strftime("%Y%m%d_%H%M%S")
        if rec.finished_at else datetime.utcnow().strftime("%Y%m%d_%H%M%S")
    )
    filename_base = f"{rec.notebook_name}_{finished_at}"

    if otype is OutputType.JSON:
        return FileResponse(
            str(path),
            media_type="application/json",
            filename=f"{filename_base}.json"
        )

    media = (
        "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        if otype is OutputType.EXCEL
        else "application/xml"
    )
    extension = ".xlsx" if otype is OutputType.EXCEL else ".xml"

    return FileResponse(
        str(path),
        media_type=media,
        filename=f"{filename_base}{extension}"
    )


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



# -------------------- CREATE ------------------------------
@app.post("/pipelines", status_code=201)
async def create_pipeline(
    dto: PipelineCreateDTO, repo: PipelineRepository = Depends(get_pipeline_repo)
):
    pipeline_id = uuid.uuid4()
    params = [
        PipelineParameterRow(
            id=uuid.uuid4(),
            pipeline_id=pipeline_id,
            name=p.name,
            type=p.type,
            value=None
        )
        for p in dto.parameters
    ]

    pipeline = PipelineRow(
        id=pipeline_id,
        name=dto.name,
        description=dto.description,
        created_at=datetime.utcnow(),
        params=params
    )

    repo.insert(pipeline)
    return {"detail": "Pipeline criado", "id": str(pipeline_id)}


@app.get("/pipelines")
async def list_pipelines(repo: PipelineRepository = Depends(get_pipeline_repo)):
    rows = repo.list_all()
    return [
        {
            "id": str(r.id),
            "name": r.name,
            "description": r.description,
            "created_at": r.created_at,
            "parameters": [
                {
                    "id": str(p.id),
                    "name": p.name,
                    "type": p.type,
                    "value": p.value
                }
                for p in r.params
            ]
        }
        for r in rows
    ]

@app.get("/pipelines/{pipeline_id}")
async def get_pipeline(
    pipeline_id: str,
    repo: PipelineRepository = Depends(get_pipeline_repo)
):
    row = repo.fetch(uuid.UUID(pipeline_id))
    if not row:
        raise HTTPException(404, "Pipeline não encontrado")

    return {
        "id": str(row.id),
        "name": row.name,
        "description": row.description,
        "created_at": row.created_at,
        "parameters": [
            {
                "id": str(p.id),
                "name": p.name,
                "type": p.type,
                "value": p.value
            }
            for p in row.params
        ]
    }


@app.put("/pipelines/{pipeline_id}", status_code=204)
async def update_pipeline(
    pipeline_id: str,
    dto: PipelineUpdateDTO,
    repo: PipelineRepository = Depends(get_pipeline_repo),
):
    existing = repo.fetch(uuid.UUID(pipeline_id))
    if not existing:
        raise HTTPException(404, "Pipeline não encontrado")

    updated_pipeline = PipelineRow(
        id=existing.id,
        name=dto.name or existing.name,
        description=dto.description or existing.description,
        created_at=existing.created_at,
        params=[
            PipelineParameterRow(
                id=uuid.uuid4(),
                pipeline_id=existing.id,
                name=p.name,
                type=p.type,
                value=None  # Resetando o valor
            )
            for p in dto.parameters
        ] if dto.parameters else existing.params
    )

    repo.update(updated_pipeline)
    return JSONResponse(status_code=204, content=None)



@app.get("/tasks", response_model=List[TaskDTO])
async def list_tasks_with_logs(repo: TaskRepository = Depends(get_task_repo)):
    rows = repo.list_tasks_with_logs()
    return [
        TaskDTO(
            request_id=row.request_id,
            notebook_name=row.notebook_name,
            version=row.version,
            params=row.params,
            status=row.status,
            retry_count=row.retry_count,
            created_at=row.created_at,
            started_at=row.started_at,
            finished_at=row.finished_at,
            output_type=row.output_type,
            output_path=row.output_path,
            error=row.error,
            logs=[
                TaskLogDTO(mensagem=log.mensagem, data=log.data)
                for log in row.logs
            ]
        )
        for row in rows
    ]
