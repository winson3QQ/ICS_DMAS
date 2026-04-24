"""
map.py — 地圖相關端點（Tiles、map_config、upload-image、cert）
"""

import sqlite3
from pathlib import Path

from fastapi import APIRouter, File, HTTPException, Request, UploadFile
from fastapi.responses import FileResponse, HTMLResponse, Response

from auth.service import get_session
from core.config import MBTILES_DIR, SRC_DIR, STATIC_DIR

router = APIRouter(tags=["地圖 Tiles"])

# CA 憑證路徑
_CERT_PATH = SRC_DIR.parent.parent / "certs" / "rootCA.pem"


def _get_tile_db(name: str) -> Path:
    p = MBTILES_DIR / f"{name}.mbtiles"
    if not p.exists():
        raise HTTPException(404, f"Tile source '{name}' not found")
    return p


@router.get("/tiles/{source}/{z}/{x}/{y}.png")
def serve_tile(source: str, z: int, x: int, y: int):
    db_path = _get_tile_db(source)
    tms_y   = (2**z - 1) - y  # Leaflet XYZ → MBTiles TMS
    with sqlite3.connect(str(db_path)) as conn:
        row = conn.execute(
            "SELECT tile_data FROM tiles WHERE zoom_level=? AND tile_column=? AND tile_row=?",
            (z, x, tms_y)).fetchone()
    if not row:
        raise HTTPException(204, "Tile not found")
    return Response(content=row[0], media_type="image/png",
                    headers={"Cache-Control": "public, max-age=86400"})


@router.get("/tiles/{source}/metadata")
def tile_metadata(source: str):
    db_path = _get_tile_db(source)
    with sqlite3.connect(str(db_path)) as conn:
        rows = conn.execute("SELECT name, value FROM metadata").fetchall()
    return {k: v for k, v in rows}


@router.get("/tiles/pmtiles/{filename}")
def serve_pmtiles(filename: str, request: Request):
    p = MBTILES_DIR / filename
    if not p.exists() or not filename.endswith(".pmtiles"):
        raise HTTPException(404, "PMTiles file not found")
    file_size    = p.stat().st_size
    range_header = request.headers.get("Range")
    if not range_header:
        return Response(content=p.read_bytes(), media_type="application/octet-stream",
                        headers={"Accept-Ranges": "bytes", "Content-Length": str(file_size)})
    try:
        _, rng      = range_header.split("=")
        start_str, end_str = rng.split("-")
        start  = int(start_str)
        end    = int(end_str) if end_str else file_size - 1
    except Exception:
        raise HTTPException(416, "Invalid Range header") from None
    if start > end or end >= file_size:
        raise HTTPException(416, "Range Not Satisfiable")
    length = end - start + 1
    with open(p, "rb") as f:
        f.seek(start)
        data = f.read(length)
    return Response(content=data, status_code=206, media_type="application/octet-stream",
                    headers={"Content-Range": f"bytes {start}-{end}/{file_size}",
                             "Accept-Ranges": "bytes", "Content-Length": str(length),
                             "Cache-Control": "public, max-age=86400"})


@router.post("/api/map_config", tags=["系統"])
async def save_map_config(request: Request):
    body        = await request.json()
    config_path = STATIC_DIR / "map_config.json"
    config_path.write_text(__import__("json").dumps(body, ensure_ascii=False, indent=2),
                           encoding="utf-8")
    return {"ok": True, "path": str(config_path)}


@router.post("/api/map/upload-image", tags=["系統"])
async def upload_map_image(request: Request, file: UploadFile = File(...)):
    token = request.headers.get("X-Session-Token")
    sess  = get_session(token) if token else None
    if not sess or sess.get("role") != "指揮官":
        raise HTTPException(403, "僅指揮官可上傳地圖")
    filename = file.filename or "map.jpg"
    ext = filename.rsplit(".", 1)[-1].lower()
    if ext not in {"jpg", "jpeg", "png", "gif", "webp", "svg"}:
        raise HTTPException(400, f"不支援的圖片格式：{ext}")
    content   = await file.read()
    save_path = STATIC_DIR / filename
    save_path.write_bytes(content)
    return {"ok": True, "filename": filename}


# CA 憑證下載
@router.get("/cert")
def download_cert():
    if not _CERT_PATH.exists():
        raise HTTPException(404, "rootCA.pem 未找到")
    return FileResponse(str(_CERT_PATH), filename="rootCA.pem")


@router.get("/cert/install", response_class=HTMLResponse)
def cert_install_page():
    return """<!DOCTYPE html>
<html lang="zh-Hant"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>安裝 CA 憑證</title></head>
<body style="font-family:sans-serif;padding:20px">
<h2>安裝 CA 根憑證</h2>
<p><a href="/cert" style="font-size:1.2em">▶ 下載 rootCA.pem</a></p>
<p>下載後依裝置說明安裝，即可信任本機伺服器的 HTTPS 憑證。</p>
</body></html>"""
