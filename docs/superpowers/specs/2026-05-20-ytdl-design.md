# YT Downloader — Design Spec

**Data:** 2026-05-20  
**Status:** Aprovado

---

## Visão Geral

Single Page Application para download de vídeos do YouTube. O usuário cola uma URL, visualiza o vídeo, escolhe o formato (MP4 ou MP3) e recebe o arquivo diretamente no browser. Progresso real exibido via polling.

---

## Stack

| Camada | Tecnologia |
|--------|------------|
| Backend | Python 3.11+ + FastAPI |
| Download | yt-dlp (nativo Python) |
| Frontend | HTML5 + Tailwind CSS (CDN) + Vanilla JS |
| Servidor de arquivos estáticos | FastAPI StaticFiles |

---

## Estrutura de Pastas

```
yt-downloader/
├── main.py                  # FastAPI app + todas as rotas
├── downloader.py            # Lógica yt-dlp (info + download)
├── requirements.txt
├── temp/                    # Arquivos temporários (runtime, não commitado)
└── static/
    └── index.html           # Frontend completo
```

---

## Arquitetura — Fluxo

```
Browser                     FastAPI
  │                            │
  ├─ POST /api/video-info ────►│ yt-dlp extrai título + thumbnail
  │◄── { title, thumbnail } ───┤
  │                            │
  ├─ POST /api/download ──────►│ inicia job em background thread
  │◄── { job_id } ─────────────┤
  │                            │
  ├─ GET /api/status/{job_id} ►│ retorna { progress, status }
  │  (polling a cada 1s)       │
  │◄── { progress: 72 } ───────┤
  │                            │
  ├─ GET /api/file/{job_id} ──►│ stream + delete após envio
  │◄── FileResponse ───────────┤
```

---

## Rotas da API

| Método | Rota | Descrição |
|--------|------|-----------|
| `GET` | `/` | Serve `static/index.html` |
| `POST` | `/api/video-info` | Valida URL, retorna `{ title, thumbnail_url }` |
| `POST` | `/api/download` | Inicia job, retorna `{ job_id }` |
| `GET` | `/api/status/{job_id}` | Retorna `{ status, progress, error }` |
| `GET` | `/api/file/{job_id}` | Stream do arquivo + deleção pós-envio |

---

## Backend — Detalhes

### `downloader.py`

- `get_video_info(url: str) -> dict` — executa `yt-dlp --dump-json <url>`, retorna `{title, thumbnail}`
- `download_video(url: str, job_id: str, format: str, temp_dir: str)` — executa yt-dlp como subprocesso com `--newline`, parseia linhas `[download] XX.X%` via regex, atualiza `jobs[job_id]`

### `main.py`

- **Estado em memória:** `jobs: dict[str, JobState]` onde `JobState = {status, progress, filepath, error}`
- **ThreadPoolExecutor** para rodar downloads sem bloquear o event loop
- **BackgroundTasks** do FastAPI para deletar arquivo após `FileResponse`

### Formatos yt-dlp

| Formato | Flags |
|---------|-------|
| MP4 | `--format "bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]" --merge-output-format mp4` |
| MP3 | `--extract-audio --audio-format mp3 --audio-quality 0` |

---

## Frontend — Detalhes

### Estados da Interface

**Estado 1 — Inicial:**
Campo de input centralizado + botão "Buscar". Validação de URL via regex antes de qualquer request.

**Estado 2 — Vídeo encontrado:**
Thumbnail + título do vídeo. Dois botões: "Baixar MP4" e "Baixar MP3".

**Estado 3 — Baixando:**
Barra de progresso animada com percentual real. Mensagem de status. Botões desabilitados.

**Estado de erro:**
Toast/banner vermelho com mensagem amigável. Retorna ao estado inicial.

### Lógica JS

- `fetchVideoInfo(url)` — POST `/api/video-info`, transiciona para estado 2
- `startDownload(format)` — POST `/api/download`, obtém `job_id`, inicia polling
- `pollStatus(job_id)` — `setInterval` 1000ms; em `done` redireciona para `/api/file/{job_id}`; em `error` exibe mensagem e limpa interval

### Visual

- **Tema:** Dark mode exclusivo
- **Paleta:** fundo `gray-950`, cards `gray-900`, bordas `gray-700`, accent `red-500`
- **Tipografia:** Inter (Google Fonts)
- **Layout:** mobile-first, `max-w-lg` centralizado no desktop

---

## Tratamento de Erros

| Cenário | Comportamento |
|---------|---------------|
| URL inválida (regex) | Erro no cliente antes de qualquer request |
| URL inválida (formato) | HTTP 400 com mensagem |
| Vídeo privado/inexistente | yt-dlp retorna erro → status `error` com mensagem amigável |
| Job não encontrado | HTTP 404 |
| Falha no download | status `error`, frontend exibe toast |

---

## Dependências

```
# requirements.txt
fastapi>=0.111.0
uvicorn[standard]>=0.29.0
yt-dlp>=2024.5.1
python-multipart>=0.0.9
```

---

## Como Rodar

```bash
pip install -r requirements.txt
python main.py
# Acesse http://localhost:8000
```

---

## Fora do Escopo

- Autenticação/login
- Histórico de downloads
- Suporte a playlists
- Seleção dinâmica de resolução
- Deploy em produção
