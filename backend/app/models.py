from enum import Enum
from pydantic import BaseModel, Field


class DocumentType(str, Enum):
    INVOICE = "INVOICE"
    PACKING_LIST = "PACKING_LIST"
    OTHER = "OTHER"


class JobStatus(str, Enum):
    QUEUED = "QUEUED"
    EXTRACTING = "EXTRACTING"
    CLASSIFYING = "CLASSIFYING"
    BUILDING = "BUILDING"
    DONE = "DONE"
    ERROR = "ERROR"


class PageResult(BaseModel):
    page_number: int = Field(..., gt=0)
    doc_type: DocumentType
    text_length: int
    used_ocr: bool
    confidence: float
    raw_label: str
    is_doc_start: bool = False


class JobState(BaseModel):
    job_id: str
    status: JobStatus
    progress: int = 0
    message: str = ""
    pages: list[PageResult] = []
    output_files: dict[str, str] = {}
    error: str | None = None
    created_at: float
    upload_file: str | None = None          # kept after pipeline for reclassification
    page_texts_preview: dict[str, str] = {}  # str(page_number) -> first 300 chars of OCR/extracted text
