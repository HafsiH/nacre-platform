from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any


class FileUploadResponse(BaseModel):
    upload_id: str
    filename: str
    rows: int | None = None
    columns: List[str] | None = None


class ConversionCreate(BaseModel):
    upload_id: str
    label_column: str
    context_columns: List[str] = []
    max_rows: Optional[int] = None
    batch_size: Optional[int] = 10  # Increased default batch size for better performance


class Candidate(BaseModel):
    code: str
    category: str
    keywords: List[str] = []


class RowClassification(BaseModel):
    row_index: int
    label_raw: str
    chosen_code: str
    chosen_category: str
    confidence: int = Field(ge=0, le=100)
    alternatives: List[Candidate] = []
    explanation: str | None = None
    evolution_summary: str | None = None
    rationale: List[str] = []


class ConversionStatus(BaseModel):
    conversion_id: str
    upload_id: str
    total_rows: int
    processed_rows: int
    status: str
    stats: Dict[str, Any] = {}


class ConversionResult(BaseModel):
    conversion_id: str
    rows: List[RowClassification]


class RowUpdate(BaseModel):
    chosen_code: Optional[str] = None
    chosen_category: Optional[str] = None
    confidence: Optional[int] = None

class ExportCreate(BaseModel):
    conversion_id: str
    columns_to_keep: List[str] = []
    include_classification: bool = True
    classification_prefix: str = "nacre_"  # nacre_code, nacre_category, nacre_confidence
