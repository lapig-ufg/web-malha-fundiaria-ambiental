from fastapi import APIRouter, Request, Response, HTTPException
from fastapi.responses import StreamingResponse
import httpx
from core.config import settings
import logging

router = APIRouter()
logger = logging.getLogger(__name__)

async def do_request(request: Request, base_url: str):
    url = request.query_params.get('url')
    if not url:
        path = request.url.path
        # Remove the router prefix if any, but since the proxy is mapped to /ows, path is likely /ows
        # Assuming the original path was requested directly on the proxy
        query_str = request.url.query
        url = f"{base_url}{path}"
        if query_str:
            url += f"?{query_str}"

    headers = {
        'Accept': request.headers.get('accept', ''),
        'User-Agent': request.headers.get('user-agent', ''),
        'X-Requested-With': request.headers.get('x-requested-with', ''),
        'Accept-Language': request.headers.get('accept-language', ''),
        'Accept-Encoding': request.headers.get('accept-encoding', '')
    }
    
    # Filter out empty headers
    headers = {k: v for k, v in headers.items() if v}

    try:
        client = httpx.AsyncClient()
        # Create a request to stream the response
        proxy_req = client.build_request(request.method, url, headers=headers)
        
        async def stream_response():
            async with client.stream(proxy_req.method, proxy_req.url, headers=proxy_req.headers) as proxy_resp:
                async for chunk in proxy_resp.aiter_bytes():
                    yield chunk

        # To handle content type correctly, we could fetch headers first, but httpx stream does that
        # We will just yield it. However, a simpler way is to use requests or just read it if it's not huge.
        # But let's use httpx streaming properly.
        # Actually, since FastAPI allows returning a StreamingResponse, we can do this:
        req = client.build_request(request.method, url, headers=headers)
        resp = await client.send(req, stream=True)
        return StreamingResponse(
            resp.aiter_bytes(),
            status_code=resp.status_code,
            headers={k: v for k, v in resp.headers.items() if k.lower() not in ("transfer-encoding", "content-encoding")}
        )

    except Exception as e:
        logger.error(f"Proxy error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/ows")
async def proxy_ows(request: Request):
    return await do_request(request, settings.OWS_HOST)

# Since original had tms but no route for it, I'll add it just in case
@router.get("/tms")
async def proxy_tms(request: Request):
    # Assuming TMS base url would exist, falling back to OWS_HOST for now
    return await do_request(request, settings.OWS_HOST)
