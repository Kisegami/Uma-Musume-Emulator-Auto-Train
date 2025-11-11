import json, os, threading
from typing import Any, Dict
from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import HTMLResponse, JSONResponse, FileResponse
from fastapi.middleware.cors import CORSMiddleware

CONFIG_PATH = os.path.join(os.path.dirname(__file__), "config.json")
_lock = threading.Lock()

def read_config() -> Dict[str, Any]:
    if not os.path.exists(CONFIG_PATH):
        raise FileNotFoundError(f"config.json not found at {CONFIG_PATH}")
    with _lock:
        with open(CONFIG_PATH, "r", encoding="utf-8") as f:
            return json.load(f)

def write_config(data: Dict[str, Any]) -> None:
    tmp_path = CONFIG_PATH + ".tmp"
    with _lock:
        with open(tmp_path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        os.replace(tmp_path, CONFIG_PATH)

app = FastAPI(title="Uma Auto Config", version="1.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], allow_credentials=True, allow_methods=["*"], allow_headers=["*"]
)

@app.get("/", response_class=HTMLResponse)
def ui():
    return FileResponse(os.path.join(os.path.dirname(__file__), "web_config.html"))

@app.get("/api/config")
def get_config():
    try:
        return read_config()
    except FileNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))

@app.put("/api/config")
async def put_config(request: Request):
    try:
        body = await request.json()
        if not isinstance(body, dict):
            raise HTTPException(status_code=400, detail="Config must be a JSON object")
        write_config(body)
        return JSONResponse({"ok": True})
    except json.JSONDecodeError:
        raise HTTPException(status_code=400, detail="Invalid JSON body")

@app.patch("/api/config")
async def patch_config(request: Request):
    try:
        updates = await request.json()
        if not isinstance(updates, dict):
            raise HTTPException(status_code=400, detail="Patch must be a JSON object")
        cfg = read_config()
        cfg.update(updates)
        write_config(cfg)
        return JSONResponse({"ok": True})
    except json.JSONDecodeError:
        raise HTTPException(status_code=400, detail="Invalid JSON body")
