import os
import uuid
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

from fastapi import FastAPI, HTTPException, BackgroundTasks
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from downloader import validate_youtube_url, get_video_info, download_video

TEMP_DIR = Path("temp")
TEMP_DIR.mkdir(exist_ok=True)

app = FastAPI()
executor = ThreadPoolExecutor(max_workers=4)
jobs: dict = {}


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
    jobs[job_id] = {"status": "queued", "progress": 0, "filepath": None, "error": None}
    executor.submit(download_video, req.url, job_id, req.format, str(TEMP_DIR), jobs)
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
        jobs.pop(job_id, None)
        if os.path.exists(filepath):
            os.remove(filepath)

    background_tasks.add_task(cleanup)
    return FileResponse(filepath, filename=os.path.basename(filepath))


app.mount("/", StaticFiles(directory="static", html=True), name="static")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
