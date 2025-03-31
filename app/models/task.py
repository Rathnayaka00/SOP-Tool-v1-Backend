from pydantic import BaseModel
from typing import Optional
from datetime import datetime

class Task(BaseModel):
    id: Optional[str] = None
    sop_id: str
    topic: str
    created_at: Optional[datetime] = None
    status: Optional[str] = "pending"
    description: Optional[str] = None 