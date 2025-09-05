from fastapi import APIRouter, UploadFile, File, HTTPException

from ..models import FileUploadResponse
from ..services.storage import save_upload
from ..services.csv_io import preview_csv
from ..services.xlsx_io import preview_xlsx
from ..utils.error_handler import validate_file_format, create_http_error


router = APIRouter()


@router.post("", response_model=FileUploadResponse)
async def upload_file(file: UploadFile = File(...)):
    try:
        validate_file_format(file.filename)
        content = await file.read()
        rec = save_upload(file.filename, content)
        stored = rec.get("path", "").lower()
        if stored.endswith(".csv"):
            cols, rows = preview_csv(rec["path"], limit=50)
            return FileUploadResponse(upload_id=rec["id"], filename=rec["filename"], rows=len(rows), columns=cols)
        if stored.endswith(".xlsx"):
            cols, rows = preview_xlsx(rec["path"], limit=50)
            return FileUploadResponse(upload_id=rec["id"], filename=rec["filename"], rows=len(rows), columns=cols)
        raise create_http_error(400, "Format non supporté. Utilisez CSV ou XLSX.", "UNSUPPORTED_FILE_FORMAT")
    except Exception as e:
        raise create_http_error(500, f"Erreur lors du traitement du fichier: {str(e)}", "FILE_PROCESSING_ERROR")


@router.get("/{upload_id}/preview", response_model=FileUploadResponse)
def get_preview(upload_id: str):
    from ..services.storage import get_upload
    up = get_upload(upload_id)
    if not up:
        raise HTTPException(status_code=404, detail="Upload introuvable")
    path = up.get("path", "").lower()
    if path.endswith('.csv'):
        cols, rows = preview_csv(up["path"], limit=50)
        return FileUploadResponse(upload_id=up["id"], filename=up["filename"], rows=len(rows), columns=cols)
    if path.endswith('.xlsx'):
        cols, rows = preview_xlsx(up["path"], limit=50)
        return FileUploadResponse(upload_id=up["id"], filename=up["filename"], rows=len(rows), columns=cols)
    raise HTTPException(status_code=400, detail="Format non supporté. Utilisez CSV ou XLSX.")
