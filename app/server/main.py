import os
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from core.config import settings

from db.session import db
from api.routes import charts, map, proxy, contact, http

app = FastAPI(title=settings.APP_NAME)

@app.on_event("startup")
async def startup():
    await db.connect()

@app.on_event("shutdown")
async def shutdown():
    await db.disconnect()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.add_middleware(GZipMiddleware, minimum_size=1000)

app.include_router(map.router, prefix="/service/map")
app.include_router(charts.router, prefix="/service/charts")
app.include_router(proxy.router)
app.include_router(contact.router, prefix="/service/contact")
app.include_router(http.router, prefix="/service/http")

# Import upload and download, but catch if they aren't fully implemented
try:
    from api.routes import upload, download
    app.include_router(upload.router, prefix="/service/upload")
    app.include_router(download.router, prefix="/service/download")
except ImportError:
    pass

# Mount angular client static files
client_dir = os.path.join(settings.app_root, settings.CLIENT_DIR)

if os.path.exists(client_dir):
    app.mount("/assets", StaticFiles(directory=os.path.join(client_dir, "assets")), name="assets")

@app.get("/{full_path:path}")
async def serve_angular_app(full_path: str):
    """Fallback route for Angular app"""
    if full_path.startswith("api/") or full_path.startswith("service/"):
        return {"error": "Not Found"}
    
    # Try serving static file if it exists
    file_path = os.path.join(client_dir, full_path)
    if os.path.exists(file_path) and os.path.isfile(file_path):
        return FileResponse(file_path)
        
    index_path = os.path.join(client_dir, "index.html")
    if os.path.exists(index_path):
        return FileResponse(index_path)
    return {"message": "Client directory not found"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=settings.PORT, reload=True)