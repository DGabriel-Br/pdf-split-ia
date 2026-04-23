# PDF Split IA

Separa automaticamente PDFs consolidados de pré-alerta em documentos individuais (faturas, packing lists, etc.) usando IA.

## Como funciona

1. Usuário faz upload de um PDF com múltiplos documentos misturados
2. O sistema extrai o texto de cada página (com OCR via Tesseract para páginas escaneadas)
3. O modelo Ollama (`llama3.1`) classifica cada página como `INVOICE`, `PACKING_LIST` ou `OTHER`
4. PDFs separados por tipo são gerados e disponibilizados para download

## Stack

- **Backend**: FastAPI + Celery + Redis
- **IA**: Ollama (`llama3.1`)
- **OCR**: Tesseract
- **Extração de PDF**: pdfplumber + PyMuPDF
- **Frontend**: React + Vite

## Pré-requisitos

- Python 3.11+
- Node.js 18+
- Redis
- [Ollama](https://ollama.com) com o modelo `llama3.1`
- [Tesseract OCR](https://github.com/tesseract-ocr/tesseract)

## Como rodar

### 1. Backend

```bash
cd backend
pip install -r requirements.txt
```

Crie o arquivo `.env` (ou edite o existente):

```ini
OLLAMA_BASE_URL=http://localhost:11434
OLLAMA_TEXT_MODEL=llama3.1
OCR_TEXT_THRESHOLD=50
OCR_CONFIDENCE_THRESHOLD=0.4
# Caminho completo do Tesseract (obrigatório no Windows; deixe vazio para usar o PATH do sistema)
TESSERACT_CMD=C:\Program Files\Tesseract-OCR\tesseract.exe
REDIS_HOST=localhost
REDIS_PORT=6379
REDIS_DB=0
STORAGE_UPLOAD_DIR=storage/uploads
STORAGE_OUTPUT_DIR=storage/outputs
MAX_UPLOAD_SIZE_MB=50
JOB_TTL_SECONDS=3600
CORS_ORIGINS=["http://localhost:5173"]
```

Inicie o Redis, o worker Celery e o servidor:

```bash
# Terminal 1 — Redis (Windows: via Docker ou Redis for Windows)
redis-server

# Terminal 2 — Celery worker
celery -A app.worker worker --pool=threads --loglevel=info

# Terminal 3 — FastAPI
uvicorn app.main:app --port 8000
```

### 2. Frontend (desenvolvimento)

```bash
cd frontend
npm install
npm run dev
```

Acesse `http://localhost:5173`.

### 3. Expor via ngrok

Para compartilhar a ferramenta externamente sem deploy, use o modo de desenvolvimento com proxy integrado do Vite:

```bash
# Terminal 1 — Backend (já deve estar rodando)
cd backend
uvicorn app.main:app --port 8000

# Terminal 2 — Frontend com proxy
cd frontend
npm run dev

# Terminal 3 — ngrok apontando para o frontend
ngrok http 5173
```

O `vite.config.js` já possui `allowedHosts: true` e proxy configurado para `/upload`, `/jobs` e `/corrections`, então o ngrok encaminha tudo corretamente com um único túnel na porta 5173.

> **Nota:** o ngrok free exibe uma tela de aviso na primeira visita. Basta clicar em "Visit Site" para continuar.

### 4. Build de produção (frontend servido pelo FastAPI)

```bash
cd frontend
npm run build
```

O FastAPI serve o `dist/` automaticamente em `http://localhost:8000`. Nesse caso, expor a porta 8000 via ngrok é suficiente:

```bash
ngrok http 8000
```

## Modelos suportados

Qualquer modelo Ollama pode ser usado. `llama3.1` oferece o melhor balanço entre precisão e velocidade para classificação de documentos de importação.
