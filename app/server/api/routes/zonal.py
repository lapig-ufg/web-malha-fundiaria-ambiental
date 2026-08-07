"""
Per-property vegetation zonal statistics endpoints.

POST /service/zonal/jobs        — start a job, returns 202 + {job_id}
GET  /service/zonal/jobs/{id}   — poll a job, returns 200/202/404

The actual rasterio work is run on a daemon thread so the FastAPI event
loop is never blocked. Job state is held in an in-memory dict, guarded
by a threading.Lock; entries older than ``ZONAL_STATISTICS_JOB_TTL_SECONDS``
are purged on every POST.
"""
import os
import threading
import time
import uuid
from typing import Any, Dict, Optional

from fastapi import APIRouter, Body, HTTPException
from pydantic import BaseModel, Field

from core.config import settings
from utils.zonal_statistics import compute_zonal_history

router = APIRouter()


# Same sentinel/landsat toggle as the "Fonte de uso e cobertura da terra"
# selector (imageSource) driving the resumo_card charts — here it picks
# which folder the APP/RL zone-mask rasters, and the Propriedade time-series
# rasters, are read from. Fixed allowlist, never built from request input
# beyond a sentinel/landsat lookup.
AUX_DIR_BY_SOURCE = {
    'sentinel': lambda: settings.ZONAL_STATISTICS_AUX_DIR_SENTINEL,
    'landsat': lambda: settings.ZONAL_STATISTICS_AUX_DIR_LANDSAT,
}

# Propriedade tab: subfolder of ZONAL_STATISTICS_RASTER_DIR holding that
# source's yearly vegetation rasters.
RASTER_DIR_SUFFIX_BY_SOURCE = {
    'sentinel': 's2',
    'landsat': 'l8',
}


def _app_rl_raster_paths(source: str) -> tuple:
    aux_dir = AUX_DIR_BY_SOURCE.get(source, AUX_DIR_BY_SOURCE['sentinel'])()
    return (
        os.path.join(aux_dir, settings.ZONAL_STATISTICS_RASTER_APP_FILENAME),
        os.path.join(aux_dir, settings.ZONAL_STATISTICS_RASTER_RL_FILENAME),
    )


def _raster_dir_for_source(source: str) -> str:
    suffix = RASTER_DIR_SUFFIX_BY_SOURCE.get(source, RASTER_DIR_SUFFIX_BY_SOURCE['sentinel'])
    return os.path.join(settings.ZONAL_STATISTICS_RASTER_DIR, suffix)


# -------- Pydantic models --------

class StartJobRequest(BaseModel):
    geometry: Dict[str, Any] = Field(..., description="GeoJSON Feature / FeatureCollection / Geometry")
    classe_vegetacao: Optional[int] = None
    input_crs: Optional[str] = "EPSG:4326"
    source: Optional[str] = "sentinel"


class StartJobResponse(BaseModel):
    job_id: str


# -------- In-memory job store --------

_lock = threading.Lock()
_jobs: Dict[str, Dict[str, Any]] = {}


def _purge_old_jobs() -> None:
    cutoff = time.time() - settings.ZONAL_STATISTICS_JOB_TTL_SECONDS
    with _lock:
        for jid in [k for k, v in _jobs.items() if v.get("created_at", 0) < cutoff]:
            _jobs.pop(jid, None)


def _run_job(
    job_id: str,
    geometry: Dict[str, Any],
    classe: int,
    input_crs: str,
    source: str,
) -> None:
    # Parse comma-separated classes_naturais from config string
    classes_naturais = tuple(
        int(c.strip().strip('"').strip("'"))
        for c in settings.ZONAL_STATISTICS_CLASSES_NATURAIS.split(",")
        if c.strip()
    )
    path_app, path_rl = _app_rl_raster_paths(source)
    raster_dir = _raster_dir_for_source(source)
    try:
        result = compute_zonal_history(
            geometry=geometry,
            raster_dir=raster_dir,
            classe_vegetacao=classe,
            input_crs=input_crs,
            path_app=path_app,
            path_rl=path_rl,
            classes_naturais=classes_naturais,
        )
        with _lock:
            _jobs[job_id]["status"] = "done"
            _jobs[job_id]["result"] = result
    except Exception as exc:  # noqa: BLE001
        with _lock:
            _jobs[job_id]["status"] = "error"
            _jobs[job_id]["error"] = str(exc)


@router.post("/jobs", status_code=202, response_model=StartJobResponse)
async def start_zonal_job(payload: StartJobRequest = Body(...)):
    if not payload.geometry or not isinstance(payload.geometry, dict):
        raise HTTPException(status_code=400, detail="Missing or invalid 'geometry'")

    _purge_old_jobs()

    classe = payload.classe_vegetacao or settings.ZONAL_STATISTICS_CLASS_VEGETACAO
    job_id = uuid.uuid4().hex

    with _lock:
        _jobs[job_id] = {
            "status": "pending",
            "created_at": time.time(),
            "result": None,
            "error": None,
        }

    # rasterio is sync/blocking; run it on a daemon thread so the loop
    # stays free and the POST returns 202 in <50ms regardless of job length.
    thread = threading.Thread(
        target=_run_job,
        args=(job_id, payload.geometry, classe, payload.input_crs or "EPSG:4326", payload.source or "sentinel"),
        daemon=True,
    )
    thread.start()
    return StartJobResponse(job_id=job_id)


@router.get("/jobs/{job_id}")
async def get_zonal_job(job_id: str):
    with _lock:
        job = _jobs.get(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="job not found")
    if job["status"] == "pending":
        return {"status": "pending"}
    if job["status"] == "error":
        return {"status": "error", "error": job["error"]}
    return {"status": "done", "result": job["result"]}
