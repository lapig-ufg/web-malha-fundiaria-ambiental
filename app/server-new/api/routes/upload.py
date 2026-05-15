import httpx
from fastapi import APIRouter, Depends, UploadFile, File, Form, HTTPException, Request
from typing import Dict

from core.config import settings
from api.dependencies import get_keycloak_token, verify_recaptcha

router = APIRouter(prefix="/service/upload", tags=["upload"])

@router.post("/savegeom", dependencies=[Depends(verify_recaptcha)])
async def save_drawed_geom(
    request: Request,
    token: dict = Depends(get_keycloak_token)
):
    body = await request.json()
    access_token = token.get("access_token")
    api = "https://task.lapig.iesa.ufg.br/api/task/savegeom"

    async with httpx.AsyncClient() as client:
        try:
            response = await client.post(
                f"{api}/geojson",
                json=body,
                headers={"Authorization": f"Bearer {access_token}", "Content-Type": "application/json"}
            )
            if response.status_code == 200:
                return {"token": response.json().get("task_id")}
        except httpx.RequestError as e:
            raise HTTPException(status_code=500, detail=str(e))
            
        raise HTTPException(status_code=500, detail="Failed to save GeoJSON")

@router.post("/savefile", dependencies=[Depends(verify_recaptcha)])
async def save_uploaded_file(
    name: str = Form(...),
    email: str = Form(...),
    files: UploadFile = File(...),
    token: dict = Depends(get_keycloak_token)
):
    if not (files.filename.endswith('.kmz') or files.filename.endswith('.zip')):
        raise HTTPException(status_code=400, detail="File upload only supports the following filetypes (.kmz or .zip ).")
        
    access_token = token.get("access_token")
    api = "https://task.lapig.iesa.ufg.br/api/task/savegeom"

    content = await files.read()
    files_data = {
        "files": (files.filename, content, files.content_type)
    }

    async with httpx.AsyncClient() as client:
        try:
            response = await client.post(
                f"{api}/file",
                params={"name": name, "email": email},
                files=files_data,
                headers={"Authorization": f"Bearer {access_token}"}
            )
            if response.status_code == 200:
                return {"token": response.json().get("task_id")}
            raise HTTPException(status_code=response.status_code, detail="Failed to upload file")
        except httpx.RequestError as e:
             raise HTTPException(status_code=500, detail=str(e))
