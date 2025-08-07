from pydantic import BaseModel, Field
from typing import Optional

class ExtractionRequest(BaseModel):
    prompt: str = Field(..., description="Natural language prompt to extract IDs and links from", min_length=1)
    
    class Config:
        json_schema_extra = {
            "example": {
                "prompt": "Compare proposal 1679 and 1680"
            }
        }

class EnhancedExtractionRequest(BaseModel):
    prompt: str = Field(..., description="Natural language prompt to extract IDs and links from", min_length=1)
    proposal_type: str = Field(default="ReferendumV2", description="Type of proposal to fetch (e.g., ReferendumV2, Discussion)")
    fetch_proposals: bool = Field(default=True, description="Whether to fetch detailed proposal information for extracted IDs")
    analyze_proposals: bool = Field(default=True, description="Whether to provide AI-powered analysis/comparison of proposals")
    
    class Config:
        json_schema_extra = {
            "example": {
                "prompt": "Compare proposal 1679 and 1680",
                "proposal_type": "ReferendumV2",
                "fetch_proposals": True,
                "analyze_proposals": True
            }
        } 