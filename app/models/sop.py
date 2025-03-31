from pydantic import BaseModel
from typing import List, Optional
from datetime import datetime

class SOP(BaseModel):
    sop_id: str
    topic: str
    description: str
    details: str
    pdf_url: str

class Task(BaseModel):
    id: Optional[str] = None
    sop_id: str
    topic: str
    created_at: Optional[datetime] = None
    status: Optional[str] = "pending"
