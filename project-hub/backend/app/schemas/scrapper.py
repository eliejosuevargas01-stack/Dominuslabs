from pydantic import BaseModel
from typing import List

class ScrapperRunPayload(BaseModel):
    queries: List[str]
    platforms: List[str]
    min_results: int
    max_results: int
