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

class AccountabilityCheckRequest(BaseModel):
    """Request model for accountability check, accepting only a prompt."""
    prompt: str = Field(..., description="Natural language prompt to extract IDs and links for accountability analysis", min_length=1)
    
    class Config:
        json_schema_extra = {
            "example": {
                "prompt": "Check accountability of proposal 1679 and discussion 3313",
            }
        }

class GeneralChatRequest(BaseModel):
    """Request model for general chat, accepting only a prompt."""
    prompt: str = Field(..., description="Natural language prompt to ask questions about proposals", min_length=1)
    
    class Config:
        json_schema_extra = {
            "example": {
                "prompt": "What are the main features of proposal 1679?",
            }
        } 