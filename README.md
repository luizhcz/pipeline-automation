# pipeline-automation

# 🧪 Pipeline Manager

Este projeto permite criar, executar e monitorar pipelines baseados em Jupyter Notebooks, com geração automática de arquivos (JSON, XML, XLSX etc).

## 🧩 Estrutura do Projeto

- **Frontend (Next.js)** – Interface de usuário para gerenciar e executar pipelines
- **Backend (FastAPI + RabbitMQ)** – API responsável pelo gerenciamento das execuções de notebooks

---

## 🚀 Instalação

### 📦 Frontend

```bash
cd frontend
npm install
npm run dev
```

### ⚙️ Backend

```bash
cd backend
python -m venv .venv
source .venv/bin/activate  # no Windows use `.venv\Scripts\activate`
pip install -r requirements.txt
uvicorn src.main:app --reload
```

> ⚠️ Certifique-se de que o RabbitMQ esteja rodando localmente (`localhost:5672`) antes de iniciar o backend.

---

## 🛠️ Como utilizar

### 1. Criar Pipeline Notebook

- Acesse a aba **"Pipelines"**
- Clique em **"Novo"** e defina:
  - Nome do pipeline (deve ser o mesmo nome do arquivo `.ipynb` no backend)
  - Descrição (opcional)
  - Parâmetros que o notebook espera (ex: `rows`, `date`, etc)

### 2. Executar Pipeline

- Vá até a aba **"Executar Pipeline"**
- Escolha um pipeline existente
- Informe os **parâmetros necessários**
- Clique em **"Executar"**

### 3. Monitorar Execução

- Acesse a aba **"Monitorar Execução"**
- Aguarde o status do pipeline mudar para **"Sucesso"**
- Clique em **"Download"** para baixar o arquivo gerado

> ⚠️ **Atenção**: o download do arquivo só estará disponível até **3 horas após a finalização** da execução.

---

## 💬 Suporte

Em caso de dúvidas ou sugestões, abra uma issue ou entre em contato com o mantenedor do projeto.

---
```
