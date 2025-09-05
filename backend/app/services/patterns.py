import json
import os
import time
from collections import defaultdict
from typing import Dict, Any

from ..config import settings


PATH = os.path.join(settings.storage_dir, "db", "patterns.json")


def _load() -> Dict[str, Any]:
    os.makedirs(os.path.join(settings.storage_dir, "db"), exist_ok=True)
    if not os.path.exists(PATH):
        return {"created_at": time.time(), "suppliers": {}, "accounts": {}}
    try:
        with open(PATH, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {"created_at": time.time(), "suppliers": {}, "accounts": {}}


def _save(obj: Dict[str, Any]):
    with open(PATH, "w", encoding="utf-8") as f:
        json.dump(obj, f, ensure_ascii=False)


def update_patterns(context: Dict[str, Any], chosen_code: str, confidence: int):
    """Update frequency maps for supplier/account → code.
    We store counts and simple avg confidence.
    """
    sup = str(context.get("fournisseur") or context.get("supplier") or context.get("Fournisseur") or "").strip().lower()
    acc = str(context.get("compte") or context.get("compte_comptable") or context.get("Compte") or "").strip().lower()
    if not sup and not acc:
        return
    data = _load()
    now = time.time()

    def _bump(bucket: Dict[str, Any], key: str):
        entry = bucket.get(key) or {"codes": {}, "updated_at": now}
        c = entry["codes"].get(chosen_code) or {"count": 0, "avg_conf": 0.0}
        # new avg
        new_count = c["count"] + 1
        new_avg = (c["avg_conf"] * c["count"] + confidence) / new_count
        entry["codes"][chosen_code] = {"count": new_count, "avg_conf": round(new_avg, 2)}
        entry["updated_at"] = now
        bucket[key] = entry

    if sup:
        suppliers = data.get("suppliers") or {}
        _bump(suppliers, sup)
        data["suppliers"] = suppliers
    if acc:
        accounts = data.get("accounts") or {}
        _bump(accounts, acc)
        data["accounts"] = accounts

    _save(data)


def get_boosts(context: Dict[str, Any]) -> Dict[str, float]:
    """Return a map code → weight based on historical patterns for supplier/account.
    Weight is proportional to frequency and confidence.
    """
    sup = str(context.get("fournisseur") or context.get("supplier") or context.get("Fournisseur") or "").strip().lower()
    acc = str(context.get("compte") or context.get("compte_comptable") or context.get("Compte") or "").strip().lower()
    data = _load()
    weights: Dict[str, float] = defaultdict(float)
    if sup and (sup in (data.get("suppliers") or {})):
        for code, stats in data["suppliers"][sup]["codes"].items():
            weights[code] += stats["count"] * (stats["avg_conf"] / 100.0)
    if acc and (acc in (data.get("accounts") or {})):
        for code, stats in data["accounts"][acc]["codes"].items():
            weights[code] += stats["count"] * (stats["avg_conf"] / 100.0)
    return dict(weights)

