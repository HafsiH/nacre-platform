import json
import os
import time
from typing import Any, Dict, List, Optional, Tuple

from openai import OpenAI

from ..config import settings, GPT5_MODELS
from .nacre_dict import get_nacre_dict, NacreEntry
from functools import lru_cache
import hashlib


INDEX_PATH = os.path.join(settings.storage_dir, "data", "nacre_index.json")

# Cache for embeddings to avoid repeated API calls
_embedding_cache: Dict[str, List[float]] = {}
_cache_max_size = 1000

_status: Dict[str, Any] = {
    "ready": False,
    "in_progress": False,
    "total": 0,
    "done": 0,
    "model": GPT5_MODELS["embeddings"],
    "last_built_at": None,
    "dict_path": None,
    "dict_mtime": None,
    "source": None,
}


def _client() -> Optional[OpenAI]:
    if not settings.openai_api_key:
        return None
    try:
        return OpenAI(api_key=settings.openai_api_key)
    except Exception:
        return None


def _embed_texts(texts: List[str]) -> List[List[float]]:
    global _embedding_cache
    
    client = _client()
    if client is None:
        return []
    
    model = _status["model"]
    results = []
    texts_to_embed = []
    indices_to_embed = []
    
    # Check cache first
    for i, text in enumerate(texts):
        text_hash = hashlib.md5(f"{model}:{text}".encode()).hexdigest()
        if text_hash in _embedding_cache:
            results.append(_embedding_cache[text_hash])
        else:
            results.append(None)  # Placeholder
            texts_to_embed.append(text)
            indices_to_embed.append(i)
    
    # Embed only uncached texts
    if texts_to_embed:
        try:
            resp = client.embeddings.create(model=model, input=texts_to_embed)
            new_embeddings = [d.embedding for d in resp.data]
            
            # Store in cache and update results
            for j, embedding in enumerate(new_embeddings):
                original_index = indices_to_embed[j]
                text = texts[original_index]
                text_hash = hashlib.md5(f"{model}:{text}".encode()).hexdigest()
                
                # Manage cache size
                if len(_embedding_cache) >= _cache_max_size:
                    # Remove oldest entries (simple FIFO)
                    oldest_key = next(iter(_embedding_cache))
                    del _embedding_cache[oldest_key]
                
                _embedding_cache[text_hash] = embedding
                results[original_index] = embedding
        except Exception:
            # Fallback: return empty embeddings for failed requests
            for i in indices_to_embed:
                results[i] = []
    
    return [r for r in results if r is not None]


def build_or_load_index(force: bool = False):
    os.makedirs(os.path.join(settings.storage_dir, "data"), exist_ok=True)
    # Determine dictionary state
    nacre = get_nacre_dict()
    dict_path = getattr(nacre, 'path', None)
    dict_mtime = None
    try:
        if dict_path and os.path.exists(dict_path):
            dict_mtime = os.path.getmtime(dict_path)
    except Exception:
        dict_mtime = None

    if (not force) and os.path.exists(INDEX_PATH):
        try:
            with open(INDEX_PATH, "r", encoding="utf-8") as f:
                idx = json.load(f)
            # Rebuild if dictionary changed or model changed
            built_from = idx.get("dict_mtime")
            same_model = idx.get("model") == _status["model"]
            if (dict_mtime and built_from and dict_mtime > built_from) or (not same_model):
                raise RuntimeError("stale index")
            _status.update({
                "ready": True,
                "in_progress": False,
                "total": len(idx.get("items", [])),
                "done": len(idx.get("items", [])),
                "last_built_at": idx.get("built_at"),
                "dict_path": dict_path,
                "dict_mtime": dict_mtime,
                "source": "loaded",
            })
            return
        except Exception:
            pass

    # Build if we can reach OpenAI
    items = nacre.entries
    _status.update({"ready": False, "in_progress": True, "total": len(items), "done": 0, "dict_path": dict_path, "dict_mtime": dict_mtime, "source": "building"})
    if _client() is None:
        # Cannot build now
        _status.update({"in_progress": False, "ready": False, "source": "unavailable"})
        return
    batch_size = 64
    embedded: List[Dict[str, Any]] = []
    for i in range(0, len(items), batch_size):
        chunk = items[i : i + batch_size]
        texts = [f"{it.category} | {' '.join(it.keywords)}" for it in chunk]
        vecs = _embed_texts(texts)
        if not vecs or len(vecs) != len(chunk):
            # abort building if embedding failed
            _status.update({"in_progress": False, "ready": False, "source": "failed"})
            return
        for it, v in zip(chunk, vecs):
            embedded.append({"code": it.code, "category": it.category, "keywords": it.keywords, "embedding": v})
        _status["done"] = min(_status["total"], i + len(chunk))
    idx_obj = {"built_at": time.time(), "model": _status["model"], "items": embedded, "dict_mtime": dict_mtime}
    with open(INDEX_PATH, "w", encoding="utf-8") as f:
        json.dump(idx_obj, f)
    _status.update({"ready": True, "in_progress": False, "last_built_at": idx_obj["built_at"], "source": "built"})


def index_status() -> Dict[str, Any]:
    return dict(_status)


def _cosine(a: List[float], b: List[float]) -> float:
    if not a or not b or len(a) != len(b):
        return 0.0
    s_ab = 0.0
    s_a = 0.0
    s_b = 0.0
    for x, y in zip(a, b):
        s_ab += x * y
        s_a += x * x
        s_b += y * y
    if s_a == 0 or s_b == 0:
        return 0.0
    import math
    return s_ab / (math.sqrt(s_a) * math.sqrt(s_b))


def retrieve_with_embeddings(query_text: str, top_k: int) -> List[Dict[str, Any]]:
    # If no index or no client, return empty to let caller fallback
    if not os.path.exists(INDEX_PATH) or _client() is None:
        return []
    with open(INDEX_PATH, "r", encoding="utf-8") as f:
        idx = json.load(f)
    qv = _embed_texts([query_text])
    if not qv:
        return []
    q = qv[0]
    scored: List[Tuple[float, Dict[str, Any]]] = []
    for it in idx.get("items", []):
        s = _cosine(q, it.get("embedding") or [])
        scored.append((s, it))
    scored.sort(key=lambda x: x[0], reverse=True)
    return [it for _, it in scored[:top_k]]
