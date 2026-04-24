# PDF Split IA — Documentação do Projeto

**Grupo Brasiliense · Setor de Importação**
Versão 1.0 · Abril de 2026

---

## 1. Visão Geral

### O que é

O **PDF Split IA** é uma ferramenta web interna que automatiza a separação de documentos de importação. PDFs consolidados recebidos durante o pré-alerta chegam com múltiplos tipos de documento misturados em um único arquivo — faturas comerciais, packing lists, certificados, Bill of Lading e outros. A ferramenta identifica cada documento usando Inteligência Artificial e gera arquivos PDF separados por tipo, prontos para uso.

### O problema que resolve

No processo manual atual, o analista precisa:

1. Abrir o PDF do pré-alerta
2. Identificar visualmente onde começa e termina cada documento
3. Recortar e salvar cada parte separadamente
4. Renomear e organizar os arquivos

Esse processo é **lento** (média de 10 a 20 minutos por embarque), **propenso a erro** (páginas esquecidas, documentos trocados) e **não rastreável** (sem log de quais páginas foram separadas e como).

### O que a ferramenta entrega

- Separação automática em segundos
- Log completo de cada página: tipo identificado, nível de confiança da IA, se foi necessário OCR
- Possibilidade de corrigir manualmente qualquer classificação antes de gerar os arquivos
- Download em um clique de todos os PDFs separados

---

## 2. Fluxo do Usuário

### Passo 1 — Acesso à ferramenta

O analista acessa a ferramenta pelo navegador. A tela inicial exibe o campo de upload centralizado com instruções claras.

> 📷 **[IMAGEM: Tela inicial — campo de upload]**

---

### Passo 2 — Envio do PDF

O analista arrasta o arquivo PDF diretamente para a área indicada, ou clica em **"Selecionar arquivo"** para buscar no computador. A ferramenta aceita arquivos de até 50 MB.

Após selecionar o arquivo, o nome do PDF é exibido confirmando a seleção. O analista clica em **"Processar PDF"** para iniciar.

> 📷 **[IMAGEM: Arquivo selecionado, botão "Processar PDF"]**

---

### Passo 3 — Processamento em tempo real

Enquanto o sistema trabalha, o analista acompanha o progresso em tempo real. A interface exibe:

- **Fase atual** com destaque visual nos três passos: Extração → Classificação → Geração
- **Mensagem de status** descrevendo o que está sendo feito (ex.: "Classificando 5 / 12 páginas...")
- **Barra de progresso** de 0% a 100%

O processamento acontece em segundo plano e não trava o navegador.

> 📷 **[IMAGEM: Tela de processamento com barra de progresso]**

---

### Passo 4 — Revisão da classificação

Ao concluir, a ferramenta exibe uma tabela com **todas as páginas do PDF original**, mostrando para cada uma:

| Campo | Descrição |
|---|---|
| **Pág.** | Número da página no PDF original |
| **Tipo** | Classificação atribuída pela IA: Invoice, Packing List ou Other |
| **Confiança** | Percentual de certeza da IA (valores abaixo de 70% são destacados em vermelho) |
| **Flags** | Indicadores especiais: `OCR` (página precisou de reconhecimento óptico) e `início` (primeira página de um novo documento) |
| **Chars** | Quantidade de caracteres extraídos da página |

O analista pode **corrigir manualmente** qualquer tipo antes de gerar os PDFs, usando o menu suspenso na coluna Tipo.

> 📷 **[IMAGEM: Tabela de revisão de classificação com badges coloridos]**

---

### Passo 5 — Download dos PDFs

Com a classificação confirmada (ou corrigida), o analista clica em **"Baixar faturas e packing lists"** e recebe um arquivo `.zip` contendo os PDFs separados:

- `INVOICE_1.pdf`, `INVOICE_2.pdf` — uma fatura por arquivo
- `PACKING_LIST_1.pdf`, `PACKING_LIST_2.pdf` — um packing list por arquivo
- `outros.pdf` — demais documentos agrupados (BL, certificados, etc.)

Se houver correções pendentes, o botão **"Aplicar correções e gerar PDFs"** reprocessa apenas a etapa de geração com os novos tipos definidos, sem precisar reenviar o arquivo.

> 📷 **[IMAGEM: Tela de resultado com botão de download e tabela de classificação]**

---

## 3. Como o Sistema Funciona

### 3.1 Pipeline de Processamento

O processamento de cada PDF percorre três fases:

```
PDF enviado
    │
    ▼
┌─────────────┐
│  EXTRAÇÃO   │  Conta páginas, extrai texto nativo do PDF
└──────┬──────┘
       │  Se página tem menos de 50 caracteres:
       │  aplica OCR (reconhecimento óptico de caracteres)
       ▼
┌─────────────┐
│CLASSIFICAÇÃO│  Analisa cada página e determina: Invoice, Packing List ou Other
└──────┬──────┘  Também detecta se é a primeira página de um documento ou continuação
       │
       ▼
┌─────────────┐
│   GERAÇÃO   │  Agrupa páginas por documento e gera os PDFs de saída
└─────────────┘
```

### 3.2 Inteligência Artificial — Como a IA classifica

A classificação de cada página passa por três camadas em ordem de prioridade:

**Camada 1 — Reconhecimento de título (mais rápido, mais confiável)**

O sistema verifica se a primeira linha da página contém um título característico. Exemplos de padrões reconhecidos:

- `"PACKING LIST"`, `"Packing List"`, `"P A C K I N G  L I S T"` → **Packing List**
- `"EXPORT INVOICE"`, `"E X P O R T  I N V O I C E"` → **Invoice**
- `"CERTIFICATE OF ORIGIN"`, `"BILL OF LADING"`, `"CONTRACT"`, `"ANNEXURE"` → **Other**

Confiança desta camada: **92–93%**

---

**Camada 2 — Análise por LLM (Inteligência Artificial generativa)**

Para páginas sem título claro, o texto é enviado a um modelo de linguagem (LLM) local rodando via [Ollama](https://ollama.com). O modelo recebe o texto da página e responde com duas palavras:

- Palavra 1: tipo do documento (`INVOICE`, `PACKING_LIST` ou `OTHER`)
- Palavra 2: posição no documento (`NEW` = primeira página, `CONT` = continuação)

O prompt foi cuidadosamente elaborado com regras de desempate para casos ambíguos, como packing lists que também mostram preços de referência (continuam sendo `PACKING_LIST`) e formulários aduaneiros que mencionam "Invoice No." em campos em branco (classificados como `OTHER`, não como fatura).

Confiança desta camada: **90–95%**

---

**Camada 3 — Contagem de palavras-chave (fallback)**

Se o LLM estiver indisponível ou retornar resposta inesperada, o sistema conta sinais específicos no texto:

- Sinais de fatura: `"payment terms"`, `"amount due"`, `"unit price"`, `"swift code"`, etc.
- Sinais de packing list: `"gross weight"`, `"net weight"`, `"cbm"`, `"cartons"`, etc.

A categoria com mais sinais vence. Confiança desta camada: **60%** (sinalizado na tabela com destaque).

---

**Pós-processamento — Detecção de faturas multi-página**

Faturas de múltiplas páginas (ex.: Robert Bosch 1/3, 2/3, 3/3) repetem o cabeçalho completo em cada página, fazendo a IA marcar cada uma como "início de novo documento". O sistema possui uma etapa de correção automática que detecta páginas consecutivas com o mesmo número de fatura e as mantém unidas no mesmo PDF de saída.

### 3.3 Extração de Texto e OCR

Para PDFs nativos (gerados digitalmente), o texto é extraído diretamente — rápido e preciso. Para PDFs escaneados (imagens), o sistema detecta automaticamente páginas com menos de 50 caracteres e aplica **OCR** (reconhecimento óptico de caracteres via EasyOCR), convertendo a imagem em texto antes de classificar.

---

## 4. Tipos de Documentos Reconhecidos

| Tipo | Código | Critério de identificação |
|---|---|---|
| **Fatura Comercial** | `INVOICE` | Documento financeiro com tabela de itens, preços unitários, totais, condições de pagamento e dados bancários. Finalidade: cobrança ao importador. |
| **Packing List** | `PACKING_LIST` | Documento logístico com pesos (bruto/líquido), CBM, contagem de caixas e dimensões. Finalidade: desembaraço aduaneiro e conferência física. |
| **Outros** | `OTHER` | Bill of Lading, Certificado de Origem, Declaração de Exportação, Fitossanitário, Contratos, Formulários aduaneiros, Capas e demais documentos. |

---

## 5. Arquitetura Técnica

| Componente | Tecnologia | Função |
|---|---|---|
| **Interface Web** | React + Vite | Tela de upload, acompanhamento em tempo real, tabela de revisão, download |
| **API** | FastAPI (Python) | Recebe o PDF, gerencia os jobs de processamento, serve os arquivos gerados |
| **Fila de tarefas** | Celery + Redis | Processa os PDFs em background sem bloquear a interface |
| **Extração de texto** | pdfplumber | Leitura nativa do texto em PDFs digitais |
| **OCR** | EasyOCR + PyMuPDF | Reconhecimento de texto em PDFs escaneados |
| **Modelo de IA** | Ollama (llama3.1) | LLM local para classificação de documentos — sem envio de dados para a nuvem |
| **Geração de PDF** | PyPDF2 | Montagem dos arquivos de saída agrupando páginas por tipo |

> **Privacidade:** Todo o processamento ocorre localmente na infraestrutura da empresa. Nenhum dado dos documentos é enviado a serviços externos.

---

## 6. Benefícios Esperados

| Indicador | Processo manual | Com PDF Split IA |
|---|---|---|
| Tempo de separação por embarque | 10–20 minutos | Menos de 1 minuto |
| Risco de erro humano (página esquecida, tipo trocado) | Alto | Baixo (log auditável + revisão assistida) |
| Rastreabilidade | Nenhuma | Log completo por página com confiança da IA |
| Escala | Limitada pela disponibilidade do analista | Ilimitada (processamento paralelo em fila) |

---

## 7. Limitações Conhecidas

- PDFs com qualidade de scan muito baixa (resolução abaixo de 100 DPI) podem ter OCR impreciso.
- Documentos em idiomas menos comuns (árabe, chinês tradicional) têm menor precisão de OCR.
- O modelo LLM (llama3.1) requer que o servidor Ollama esteja em execução na máquina de produção.

---

*Documento elaborado pelo Setor de TI · Grupo Brasiliense · Abril de 2026*
