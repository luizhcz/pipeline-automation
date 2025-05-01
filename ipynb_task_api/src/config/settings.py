import os
import re
from pathlib import Path
from typing import Dict, List, Annotated
from dotenv import load_dotenv

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings

# Define qual ambiente será carregado
ENV = os.getenv("ENV", "dev")
dotenv_path = Path(__file__).parent.parent.parent / f".env.{ENV}"

# Carrega o arquivo .env correto
if dotenv_path.exists():
    load_dotenv(dotenv_path)
else:
    raise FileNotFoundError(f"Arquivo {dotenv_path} não encontrado")


class AppSettings(BaseSettings):
    ENV: str
    sql_server_connection_string : str
    rabbitmq_url: str 
    task_queue: str
    dlq_queue: str
    max_retries: int
    notebook_timeout: int
    base_dir: Path = Path(__file__).resolve().parent.parent.parent

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

    class Config:
        case_sensitive = False


settings = AppSettings()