from pydantic import BaseModel
from typing import List

class Embedding(BaseModel):
    sop_id: str
    topic_embedding: List[float]
    summary_embedding: List[float] 