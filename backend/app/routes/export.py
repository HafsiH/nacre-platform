from io import StringIO
import csv
from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse

from ..models import ExportCreate
from ..services.storage import get_conversion, get_upload
from ..services.csv_io import iterate_csv
from ..services.xlsx_io import iterate_xlsx


router = APIRouter()


@router.post("", response_class=StreamingResponse)
def export_csv(payload: ExportCreate):
    conv = get_conversion(payload.conversion_id)
    if not conv:
        raise HTTPException(status_code=404, detail="Conversion introuvable")
    up = get_upload(conv.get("upload_id"))
    if not up:
        raise HTTPException(status_code=404, detail="Upload introuvable")
    up_path = up.get("path")
    if not up_path:
        raise HTTPException(status_code=400, detail="Chemin upload manquant")

    # Build a map from row_index -> classification info
    by_idx = {int(r.get("row_index", i)): r for i, r in enumerate(conv.get("rows", []))}

    # Prepare CSV output in memory
    buf = StringIO()
    writer = None

    # Iterate original CSV and write selected columns + classification
    iterator = None
    if up_path.lower().endswith('.csv'):
        iterator = iterate_csv(up_path)
    elif up_path.lower().endswith('.xlsx'):
        iterator = iterate_xlsx(up_path)
    else:
        raise HTTPException(status_code=400, detail="Format non supporté (CSV/XLSX)")

    for i, row in enumerate(iterator):
        out = {}
        for col in payload.columns_to_keep:
            if col in row:
                out[col] = row[col]
        if payload.include_classification:
            cls = by_idx.get(i)
            if cls:
                pref = payload.classification_prefix
                out[f"{pref}code"] = cls.get("chosen_code", "")
                out[f"{pref}category"] = cls.get("chosen_category", "")
                out[f"{pref}confidence"] = cls.get("confidence", "")
        if writer is None:
            # Initialize with discovered headers (stable order: input cols then cls)
            headers = list(out.keys())
            writer = csv.DictWriter(buf, fieldnames=headers)
            writer.writeheader()
        writer.writerow(out)

    filename = f"export_{payload.conversion_id}.csv"
    buf.seek(0)
    return StreamingResponse(
        buf,
        media_type="text/csv",
        headers={"Content-Disposition": f"attachment; filename={filename}"},
    )
