from fastapi import APIRouter
from pydantic import BaseModel
import os
import time
from typing import Optional
import httpx

from ..config import settings
from ..services.nacre_dict import get_nacre_dict, reset_nacre_dict
from ..services.embeddings import index_status
from ..services.sophie import initialize_sophie, sophie_status
from ..services.document_access import invalidate_document_cache
from ..services.co2_analyzer import co2_analyzer


class HealthResponse(BaseModel):
    ok: bool
    api: bool
    openai_key_present: bool
    openai_connectivity: Optional[bool] = None
    dict_loaded: bool
    dict_entries: int
    storage_ok: bool
    checked_at: float
    learning: dict
    sophie: dict
    co2_analyzer: dict


router = APIRouter()


@router.get("")
def health() -> HealthResponse:
    api_ok = True
    key_present = bool(settings.openai_api_key)

    # Check OpenAI endpoint reachability (without generating tokens)
    oa_conn: Optional[bool] = None
    if key_present:
        try:
            headers = {"Authorization": f"Bearer {settings.openai_api_key}"}
            with httpx.Client(timeout=2.0) as client:
                r = client.get("https://api.openai.com/v1/models", headers=headers)
            oa_conn = r.status_code < 500
        except Exception:
            oa_conn = False

    # Check dictionary
    try:
        d = get_nacre_dict()
        dict_entries = len(d.entries)
        dict_ok = dict_entries > 0
    except Exception:
        dict_ok = False
        dict_entries = 0

    # Check storage write/cleanup
    storage_ok = True
    try:
        tmp_dir = os.path.join(settings.storage_dir, "tmp")
        os.makedirs(tmp_dir, exist_ok=True)
        probe = os.path.join(tmp_dir, "health_probe.txt")
        with open(probe, "w", encoding="utf-8") as f:
            f.write("ok")
        os.remove(probe)
    except Exception:
        storage_ok = False

    overall_ok = api_ok and dict_ok and storage_ok and (oa_conn is not False)

    # Check CO2 analyzer
    co2_status = {}
    try:
        co2_status = co2_analyzer.get_status()
    except Exception as e:
        co2_status = {"status": "error", "error": str(e)}

    return HealthResponse(
        ok=overall_ok,
        api=api_ok,
        openai_key_present=key_present,
        openai_connectivity=oa_conn,
        dict_loaded=dict_ok,
        dict_entries=dict_entries,
        storage_ok=storage_ok,
        checked_at=time.time(),
        learning=index_status(),
        sophie=sophie_status(),
        co2_analyzer=co2_status,
    )


@router.post("/reset-connections")
def reset_connections() -> dict:
    """Reset API and OpenAI connections by clearing caches and reinitializing services"""
    try:
        # Clear any cached connections or states
        invalidate_document_cache()
        
        # Reinitialize Sophie (which tests OpenAI connectivity)
        initialize_sophie()
        
        # Force a fresh health check
        health_result = health()
        
        return {
            "ok": True, 
            "message": "Connexions réinitialisées",
            "health": {
                "api": health_result.api,
                "openai_connectivity": health_result.openai_connectivity,
                "dict_loaded": health_result.dict_loaded,
                "co2_analyzer": health_result.co2_analyzer
            }
        }
    except Exception as e:
        return {
            "ok": False,
            "message": f"Erreur lors de la réinitialisation: {str(e)}"
        }

@router.post("/rebuild")
def rebuild_index() -> dict:
    from ..services.embeddings import build_or_load_index
    build_or_load_index(force=True)
    initialize_sophie()
    invalidate_document_cache()
    reset_nacre_dict()
    return {"ok": True, "learning": index_status(), "sophie": sophie_status()}
