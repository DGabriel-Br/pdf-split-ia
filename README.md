# PDF Split IA

Separa automaticamente PDFs consolidados de pré-alerta de importação em arquivos individuais por tipo de documento (faturas e packing lists), usando OCR e classificação por IA.

## Requisitos

- [Python 3.11+](https://www.python.org/downloads/)
- [Node.js 18+](https://nodejs.org/)
- [Docker](https://www.docker.com/) (para o Redis)
- [Tesseract OCR](https://github.com/UB-Mannheim/tesseract/wiki)
- [Ollama](https://ollama.com/) com o modelo `llama3.1`
- [ngrok](https://ngrok.com/) instalado como serviço Windows (opcional, para acesso externo)

## Configuração inicial

**1. Crie o container Redis**
```bash
docker run -d --name redis-pdfsplit -p 6379:6379 redis:7-alpine
```

**2. Baixe o modelo de IA**
```bash
ollama pull llama3.1
```

**3. Instale as dependências do backend**
```bash
cd backend
pip install -r requirements.txt
```

**4. Instale as dependências do frontend**
```bash
cd frontend
npm install
```

**5. Configure o backend**

Crie o arquivo `backend/.env` com base no exemplo abaixo:
```ini
OLLAMA_BASE_URL=http://localhost:11434
OLLAMA_TEXT_MODEL=llama3.1
OCR_TEXT_THRESHOLD=50
OCR_CONFIDENCE_THRESHOLD=0.4
TESSERACT_CMD=C:\Program Files\Tesseract-OCR\tesseract.exe
REDIS_HOST=localhost
REDIS_PORT=6379
STORAGE_UPLOAD_DIR=storage/uploads
STORAGE_OUTPUT_DIR=storage/outputs
MAX_UPLOAD_SIZE_MB=50
JOB_TTL_SECONDS=3600
CORS_ORIGINS=["http://localhost:5173"]
```

> `TESSERACT_CMD` deve conter o caminho completo do executável no Windows. Em Linux/Mac, deixe vazio para usar o PATH do sistema.

## Como usar

Execute `start.bat` na raiz do projeto. Ele inicia todos os serviços automaticamente.

Acesse em `http://localhost:5173`.
