from pydantic import BaseModel
from typing import List, Optional
from datetime import datetime

class SOP(BaseModel):
    sop_id: str
    topic: str
    description: str
    details: str
    pdf_url: str
    effectiveness_score: Optional[float] = None

class SOPDocument(BaseModel):
    sop_id: str
    topic: str
    pdf_url: str
    created_at: datetime
    effectiveness_score: Optional[float] = None
    version: int = 1


class Task(BaseModel):
    id: str
    sop_id: str
    topic: str
    created_at: datetime
    status: str

class EditedSOPDetails(BaseModel):
    new_sop_id: str
    old_sop_id: str
    original_details: str
    edited_details: str
    pdf_url: str
    created_at: datetime
    effectiveness_score: float
    version: int
