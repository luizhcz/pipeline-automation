FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# Instala dependências de sistema e drivers ODBC
RUN apt-get update && apt-get install -y \
    curl \
    gnupg \
    unixodbc \
    unixodbc-dev \
    gcc \
    g++ \
    apt-transport-https \
    ca-certificates \
    && rm -rf /var/lib/apt/lists/*

# Instala driver Microsoft ODBC 17 para SQL Server
RUN curl https://packages.microsoft.com/keys/microsoft.asc | apt-key add - && \
    curl https://packages.microsoft.com/config/debian/10/prod.list > /etc/apt/sources.list.d/mssql-release.list && \
    apt-get update && ACCEPT_EULA=Y apt-get install -y msodbcsql17 && \
    apt-get clean

# Define diretório de trabalho
WORKDIR /app

# Copia os arquivos do backend
COPY . /app

# Instala dependências Python
WORKDIR /app/src
RUN pip install --upgrade pip
RUN pip install -r requirements.txt

EXPOSE 8000

# Inicia a API FastAPI
CMD ["uvicorn", "api.main:app", "--host", "0.0.0.0", "--port", "8000"]
