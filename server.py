import os
import uuid
from pathlib import Path
from fastapi import FastAPI, UploadFile, File, Header, HTTPException
from fastapi.responses import FileResponse
from starlette.status import HTTP_401_UNAUTHORIZED

API_KEY = os.environ.get("REPLAY_API_KEY", "")
STORAGE_DIR = Path(os.environ.get("REPLAY_STORAGE_DIR", "./storage"))
STORAGE_DIR.mkdir(parents=True, exist_ok=True)

app = FastAPI()

def check_auth(x_api_key: str | None, authorization: str | None):
    bearer = None
    if authorization and authorization.lower().startswith("bearer "):
        bearer = authorization.split(" ", 1)[1].strip()
    provided = x_api_key or bearer
    if not API_KEY or provided != API_KEY:
        raise HTTPException(status_code=HTTP_401_UNAUTHORIZED, detail="Unauthorized")

@app.get("/files")
def list_files(
    x_api_key: str | None = Header(default=None, convert_underscores=False),
    authorization: str | None = Header(default=None),
):
    check_auth(x_api_key, authorization)
    files = []
    for p in STORAGE_DIR.glob("*.json"):
        files.append({"file_id": p.stem, "name": p.name, "type": "application/json"})
    return {"files": files}

@app.post("/upload")
async def upload_file(
    input_type: str | None = None,  # Unity calls /upload?input_type=file
    file: UploadFile = File(...),   # multipart field must be named "file"
    x_api_key: str | None = Header(default=None, convert_underscores=False),
    authorization: str | None = Header(default=None),
):
    check_auth(x_api_key, authorization)

    data_key = uuid.uuid4().hex
    save_path = STORAGE_DIR / f"{data_key}.json"
    content = await file.read()
    save_path.write_bytes(content)

    # Unity expects {"data_key": "..."}
    return {"data_key": data_key}

@app.get("/download")
def download(
    data_key: str,
    x_api_key: str | None = Header(default=None, convert_underscores=False),
    authorization: str | None = Header(default=None),
):
    check_auth(x_api_key, authorization)
    path = STORAGE_DIR / f"{data_key}.json"
    if not path.exists():
        raise HTTPException(status_code=404, detail="Not found")

    # Unity reads raw bytes from response body
    return FileResponse(path, media_type="application/json", filename="downloaded_data.json")
