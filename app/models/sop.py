from pydantic import BaseModel
from typing import List, Optional
from datetime import datetime

class SOP(BaseModel):
    sop_id: str
    topic: str
    description: str
    details: str
    pdf_url: str

class SOPDocument(BaseModel):
    sop_id: str
    topic: str
    pdf_url: str
    created_at: datetime
    percentage: Optional[int] = 0

class EditedSOPDocument(BaseModel):
    new_sop_id: str
    old_sop_id: str
    topic: str
    details: str
    version: int
    created_at: datetime

class Task(BaseModel):
    id: Optional[str] = None
    sop_id: str
    topic: str
    created_at: Optional[datetime] = None
    status: Optional[str] = "pending"
    percentage: Optional[int] = 0