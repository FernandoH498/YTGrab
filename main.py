import os
import uuid
import threading
from concurrent.futures import ThreadPoolExecutor
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, HTTPException, BackgroundTasks, Request
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from downloader import validate_youtube_url, get_video_info, download_video

TEMP_DIR = Path("temp")
TEMP_DIR.mkdir(exist_ok=True)

executor = ThreadPoolExecutor(max_workers=4)
jobs: dict = {}
jobs_lock = threading.Lock()


@asynccontextmanager
async def lifespan(app: FastAPI):
    cookies = os.getenv("YOUTUBE_COOKIES", "").strip()
    if cookies:
        cookies = cookies.replace("\\n", "\n")
        Path("cookies.txt").write_text(cookies, newline="\n")
    yield
    executor.shutdown(wait=False)


app = FastAPI(lifespan=lifespan)


@app.exception_handler(Exception)
async def unhandled_exception_handler(request: Request, exc: Exception):
    return JSONResponse(status_code=500, content={"detail": "Erro interno no servidor. Tente novamente."})


class VideoInfoRequest(BaseModel):
    url: str


class DownloadRequest(BaseModel):
    url: str
    format: str


@app.post("/api/video-info")
def api_video_info(req: VideoInfoRequest):
    if not validate_youtube_url(req.url):
        raise HTTPException(status_code=400, detail="URL do YouTube inválida")
    try:
        return get_video_info(req.url)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.post("/api/download")
def api_download(req: DownloadRequest):
    if not validate_youtube_url(req.url):
        raise HTTPException(status_code=400, detail="URL do YouTube inválida")
    if req.format not in ("mp4", "mp3"):
        raise HTTPException(status_code=400, detail="Formato inválido. Use 'mp4' ou 'mp3'.")
    job_id = str(uuid.uuid4())
    with jobs_lock:
        jobs[job_id] = {"status": "queued", "progress": 0, "filepath": None, "error": None}
    executor.submit(download_video, req.url, job_id, req.format, str(TEMP_DIR), jobs, jobs_lock)
    return {"job_id": job_id}


@app.get("/api/status/{job_id}")
def api_status(job_id: str):
    if job_id not in jobs:
        raise HTTPException(status_code=404, detail="Job não encontrado")
    job = jobs[job_id]
    return {"status": job["status"], "progress": job["progress"], "error": job["error"]}


@app.get("/api/file/{job_id}")
def api_file(job_id: str, background_tasks: BackgroundTasks):
    if job_id not in jobs:
        raise HTTPException(status_code=404, detail="Job não encontrado")
    job = jobs[job_id]
    if job["status"] != "done":
        raise HTTPException(status_code=400, detail="Download ainda não concluído")
    filepath = job["filepath"]
    if not filepath or not os.path.exists(filepath):
        raise HTTPException(status_code=404, detail="Arquivo não encontrado no servidor")

    def cleanup():
        with jobs_lock:
            jobs.pop(job_id, None)
        if os.path.exists(filepath):
            os.remove(filepath)

    background_tasks.add_task(cleanup)
    return FileResponse(filepath, filename=os.path.basename(filepath))


@app.get("/", include_in_schema=False)
def serve_index():
    return FileResponse("static/index.html", headers={"Cache-Control": "no-cache, no-store, must-revalidate"})


app.mount("/", StaticFiles(directory="static", html=True), name="static")

if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", "8000"))
    uvicorn.run("main:app", host="0.0.0.0", port=port, reload=False)
