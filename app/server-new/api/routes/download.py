import os
import httpx
import zipfile
import tempfile
from fastapi import APIRouter, HTTPException, BackgroundTasks
from fastapi.responses import FileResponse
from pydantic import BaseModel
from typing import Dict, Any, Optional

from core.config import settings

router = APIRouter(prefix="/service", tags=["download"])

class DownloadRequest(BaseModel):
    layer: Dict[str, Any]
    region: Dict[str, Any]
    filter: Optional[Dict[str, Any]] = None
    typeDownload: str

async def request_file_from_mapserver(url: str, path_file: str, layer_name: str, type_download: str):
    """
    Simulates the download from the map server and packing it into a ZIP.
    """
    async with httpx.AsyncClient() as client:
        try:
            # Download main data
            response = await client.get(url)
            response.raise_for_status()
            
            with open(f"{path_file}.tmp", 'wb') as f:
                f.write(response.content)
            
            # Create ZIP
            with zipfile.ZipFile(f"{path_file}.zip", 'w', zipfile.ZIP_DEFLATED) as zipf:
                zipf.write(f"{path_file}.tmp", arcname=f"{layer_name}.{type_download}")
                
                # Fetch SLD if not CSV
                if type_download != 'csv':
                    ows_url = getattr(settings, 'OWS_HOST', 'http://localhost/ows')
                    sld_url = f"{ows_url}?request=GetStyles&layers={layer_name}&service=wms&version=1.1.1"
                    sld_response = await client.get(sld_url)
                    if sld_response.status_code == 200:
                        zipf.writestr(f"{layer_name}.sld", sld_response.content)
            
            os.remove(f"{path_file}.tmp")
        except Exception as e:
            if os.path.exists(f"{path_file}.tmp"):
                os.remove(f"{path_file}.tmp")
            raise Exception(f"Error fetching from mapserver: {e}")

@router.post("/download")
async def download_geo_file(request: DownloadRequest, background_tasks: BackgroundTasks):
    layer = request.layer
    region = request.region
    filter_data = request.filter
    type_download = request.typeDownload

    layer_name = layer.get('filterSelected', layer.get('valueType', 'unknown_layer'))
    file_param = layer.get('valueType', 'layer')
    
    if filter_data:
        file_param = f"{file_param}_{filter_data.get('valueFilter', '')}"

    region_type = region.get('type', 'all')
    region_value = region.get('value', 'all')
    
    download_dir = getattr(settings, 'DOWNLOAD_DIR', '/tmp/downloads/')
    directory = os.path.join(download_dir, region_type, str(region_value), type_download, layer.get('valueType', 'layer'))
    
    if not os.path.exists(directory):
        os.makedirs(directory, exist_ok=True)
        
    path_file = os.path.join(directory, file_param)
    
    if os.path.exists(f"{path_file}.zip"):
        return FileResponse(f"{path_file}.zip", media_type="application/zip", filename=f"{file_param}.zip")
    
    # Mocking mapserver URL since DownloadBuilder is complex to fully port in one go
    # In a full migration, the DownloadBuilder class logic would construct this URL
    mapserver_url = getattr(settings, 'OWS_HOST', 'http://localhost/ows') + f"?service=WFS&version=1.0.0&request=GetFeature&typeName={layer_name}&outputFormat={type_download}"
    
    try:
        await request_file_from_mapserver(mapserver_url, path_file, layer_name, type_download)
        return FileResponse(f"{path_file}.zip", media_type="application/zip", filename=f"{file_param}.zip")
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))
