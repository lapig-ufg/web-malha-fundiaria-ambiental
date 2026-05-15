import httpx
from fastapi import Request, HTTPException, Header, Depends
from db.session import db
import importlib
from core.config import settings

async def get_keycloak_token():
    payload = {
        "client_id": settings.AUTH_ID,
        "client_secret": settings.AUTH_SECRET,
        "grant_type": "client_credentials",
    }
    
    auth_url = getattr(settings, 'AUTH_URL', 'http://localhost')
    auth_realm = getattr(settings, 'AUTH_REALM', 'realm')
    
    api_url = f"{auth_url}/realms/{auth_realm}/protocol/openid-connect/token"
    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(api_url, data=payload)
            if response.status_code == 200:
                return response.json()
            else:
                raise HTTPException(status_code=401, detail="Keycloak auth failed")
    except Exception as e:
        # For development/fallback if AUTH_URL is not configured
        if not settings.AUTH_URL:
            return {"access_token": "mock_token"}
        raise HTTPException(status_code=501, detail=str(e))

async def verify_recaptcha(recaptcha_token: str = Header(None, alias="recaptcha-token")):
    if not recaptcha_token:
        raise HTTPException(status_code=401, detail="You are a robot (missing token)")
        
    api = 'https://www.google.com/recaptcha/api/siteverify'
    secret = getattr(settings, 'RECAPTCHA_KEY', '')
    
    if not secret:
        # Skip verification if key is not configured (dev mode)
        return True
        
    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(
                api,
                data={"secret": secret, "response": recaptcha_token}
            )
            data = response.json()
            if data.get("success"):
                return True
            else:
                raise HTTPException(status_code=401, detail="You are a robot")
    except Exception as e:
        raise HTTPException(status_code=501, detail="Server error during recaptcha verification")

async def data_injector(request: Request):
    path_parts = request.url.path.split('/')
    if len(path_parts) < 4:
        return
        
    controller_name = path_parts[2]
    method_name = path_parts[3]
    
    try:
        query_module = importlib.import_module(f"db.queries.{controller_name}")
        queries_func = getattr(query_module, "get_queries")
        
        # Merge params from path, query and body
        params = dict(request.query_params)
        params.update(request.path_params)
        
        # Try to get body if it's JSON
        try:
            body = await request.json()
            if isinstance(body, dict):
                params.update(body)
        except:
            pass
            
        all_queries = queries_func(params)
        
        if method_name in all_queries:
            method_queries_factory = all_queries[method_name]
            method_queries = method_queries_factory(params)
            
            if isinstance(method_queries, str):
                method_queries = [{
                    'id': method_name,
                    'sql': method_queries
                }]
                
            results = {}
            for q in method_queries:
                query_result = await db.query(q, params)
                results[q['id']] = query_result
                
            # Matching JS logic for single result
            if len(results) == 1 and not method_queries[0].get('mantain', False):
                keys = list(results.keys())
                results = results[keys[0]]
                
            request.state.query_result = results
    except (ImportError, AttributeError) as e:
        # If no query found, just continue
        pass
    except Exception as e:
        print(f"Data Injector Error: {e}")
        raise HTTPException(status_code=500, detail=str(e))
