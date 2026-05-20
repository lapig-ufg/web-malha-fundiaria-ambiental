from fastapi import APIRouter, Request, HTTPException
from pydantic import BaseModel
import httpx
import logging

router = APIRouter()
logger = logging.getLogger(__name__)

class HttpGetRequest(BaseModel):
    url: str

@router.post("/get")
async def http_get(request: HttpGetRequest):
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(request.url)
            response.raise_for_status()
            return {"data": response.text}
    except Exception as e:
        logger.error(f"HTTP GET error for {request.url}: {e}")
        raise HTTPException(status_code=400, detail=str(e))
