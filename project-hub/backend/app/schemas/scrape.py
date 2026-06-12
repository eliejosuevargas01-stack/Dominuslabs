from pydantic import BaseModel, Field
from typing import List, Optional

class ScrapePayload(BaseModel):
    queries: List[str]
    max_results: Optional[int] = 10
    min_results: Optional[int] = None
    target_platform: Optional[str] = None
    webhook_url: Optional[str] = None
