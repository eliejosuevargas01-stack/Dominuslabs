from pydantic import BaseModel
from typing import List, Optional

class ScrapperRunPayload(BaseModel):
    queries: List[str]
    min_results: int
    max_results: int
    target_platform: Optional[List[str]] = None
    contact_channel: Optional[List[str]] = None
    objective: Optional[str] = None
