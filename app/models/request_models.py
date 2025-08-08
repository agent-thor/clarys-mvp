from pydantic import BaseModel, Field, ConfigDict
from typing import Optional

class ExtractionRequest(BaseModel):
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "prompt": "Compare proposal 1679 and 1680"
            }
        }
    )
    
    prompt: str = Field(..., description="Natural language prompt to extract IDs and links from", min_length=1)
    
class EnhancedExtractionRequest(BaseModel):
    """Request model for enhanced extraction, accepting only a prompt."""
    prompt: str = Field(..., description="Natural language prompt to extract IDs and links from", min_length=1)
    
    class Config:
        json_schema_extra = {
            "example": {
                "prompt": "Compare proposal 1679 with the discussion at @https://polkadot.polkassembly.io/post/3313",
            }
        } 