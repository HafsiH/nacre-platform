import json
import os
import shutil
import uuid
from typing import Any

from ..config import settings


def ensure_dirs():
    os.makedirs(os.path.join(settings.storage_dir, "uploads"), exist_ok=True)
    os.makedirs(os.path.join(settings.storage_dir, "data"), exist_ok=True)
    os.makedirs(os.path.join(settings.storage_dir, "db"), exist_ok=True)


def save_upload(filename: str, file_bytes: bytes) -> dict[str, Any]:
    ensure_dirs()
    uid = str(uuid.uuid4())
    path = os.path.join(settings.storage_dir, "uploads", f"{uid}__{filename}")
    with open(path, "wb") as f:
        f.write(file_bytes)
    rec = {"id": uid, "filename": filename, "path": path}
    _put_json(f"upload_{uid}.json", rec)
    return rec


def get_upload(upload_id: str) -> dict[str, Any] | None:
    return _get_json(f"upload_{upload_id}.json")


def create_conversion(upload_id: str, meta: dict[str, Any]) -> dict[str, Any]:
    ensure_dirs()
    cid = str(uuid.uuid4())
    rec = {
        "id": cid,
        "upload_id": upload_id,
        "status": "running",
        "processed_rows": 0,
        "total_rows": 0,
        "stats": {},
        "meta": meta,
        "rows": [],
    }
    _put_json(f"conv_{cid}.json", rec)
    return rec


def update_conversion(conv_id: str, patch: dict[str, Any]) -> dict[str, Any]:
    rec = _get_json(f"conv_{conv_id}.json") or {}
    rec.update(patch)
    _put_json(f"conv_{conv_id}.json", rec)
    return rec


def append_conversion_row(conv_id: str, row_rec: dict[str, Any]):
    try:
        rec = _get_json(f"conv_{conv_id}.json") or {}
        rows = rec.get("rows", [])
        rows.append(row_rec)
        rec["rows"] = rows
        rec["processed_rows"] = len(rows)
        _put_json(f"conv_{conv_id}.json", rec)
    except Exception as e:
        print(f"❌ Error appending row to conversion {conv_id}: {e}")
        import traceback
        traceback.print_exc()
        raise


def get_conversion(conv_id: str) -> dict[str, Any] | None:
    return _get_json(f"conv_{conv_id}.json")


def _db_path(name: str) -> str:
    return os.path.join(settings.storage_dir, "db", name)


def _put_json(name: str, obj: dict[str, Any]):
    try:
        ensure_dirs()  # Make sure directories exist
        path = _db_path(name)
        print(f"💾 Writing JSON to: {path}")
        with open(path, "w", encoding="utf-8") as f:
            json.dump(obj, f, ensure_ascii=False, indent=2)
        print(f"✅ Successfully wrote JSON: {name}")
    except Exception as e:
        print(f"❌ Error writing JSON {name}: {e}")
        import traceback
        traceback.print_exc()
        raise


def _get_json(name: str) -> dict[str, Any] | None:
    try:
        path = _db_path(name)
        if not os.path.exists(path):
            print(f"📂 JSON file not found: {path}")
            return None
        print(f"📖 Reading JSON from: {path}")
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        print(f"✅ Successfully read JSON: {name}")
        return data
    except Exception as e:
        print(f"❌ Error reading JSON {name}: {e}")
        import traceback
        traceback.print_exc()
        return None

