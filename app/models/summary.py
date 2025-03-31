from pydantic import BaseModel

class SOPSummary(BaseModel):
    topic_id: str
    sop_id: str
    summary: str
