from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any

class ProposalInfo(BaseModel):
    id: str = Field(description="Proposal ID")
    title: str = Field(description="Proposal title")
    content: str = Field(description="Proposal content")
    status: str = Field(description="Proposal status")
    created_at: str = Field(description="Creation timestamp")
    proposer: Optional[str] = Field(default=None, description="Proposer address")
    beneficiaries: Optional[List[Dict[str, Any]]] = Field(default=None, description="Proposal beneficiaries")
    vote_metrics: Optional[Dict[str, Any]] = Field(default=None, description="Voting metrics")
    timeline: Optional[List[Dict[str, Any]]] = Field(default=None, description="Proposal timeline")
    error: Optional[str] = Field(default=None, description="Error message if fetch failed")

class ExtractionResponse(BaseModel):
    ids: List[str] = Field(default=[], description="List of extracted IDs")
    links: List[str] = Field(default=[], description="List of extracted URLs")
    
    class Config:
        json_schema_extra = {
            "example": {
                "ids": ["1679", "1680"],
                "links": ["https://polkadot.polkassembly.io/referenda/1679"]
            }
        }

class EnhancedExtractionResponse(BaseModel):
    ids: List[str] = Field(default=[], description="List of extracted IDs")
    links: List[str] = Field(default=[], description="List of extracted URLs")
    proposals: List[ProposalInfo] = Field(default=[], description="Detailed proposal information for extracted IDs")
    analysis: Optional[str] = Field(default=None, description="AI-powered analysis or comparison of proposals")
    
    class Config:
        json_schema_extra = {
            "example": {
                "ids": ["1679", "1680"],
                "links": [],
                "proposals": [
                    {
                        "id": "1679",
                        "title": "CLARYS.AI Beta Product Development",
                        "content": "## Why do we need Clarys.AI?...",
                        "status": "Deciding",
                        "created_at": "2025-07-18T07:26:49.489Z",
                        "proposer": "146ZZqm2cMHLf3ju7oc8M9JnPaAktuADAKThagKnXqzjPJbZ",
                        "error": None
                    }
                ],
                "analysis": "Proposal 1679:\nTitle: CLARYS.AI Beta Product Development\n...\nComparison:\nCost: Proposal 1679 requests 129K USDC..."
            }
        }

class AccountabilityCheckResponse(BaseModel):
    ids: List[str] = Field(default=[], description="List of extracted IDs")
    links: List[str] = Field(default=[], description="List of extracted URLs")
    proposals: List[ProposalInfo] = Field(default=[], description="Detailed proposal information for extracted IDs")
    accountability_analysis: Optional[str] = Field(default=None, description="AI-powered accountability analysis of proposals")
    
    class Config:
        json_schema_extra = {
            "example": {
                "ids": ["1679"],
                "links": [],
                "proposals": [
                    {
                        "id": "1679",
                        "title": "CLARYS.AI Beta Product Development",
                        "content": "## Why do we need Clarys.AI?...",
                        "status": "Deciding",
                        "created_at": "2025-07-18T07:26:49.489Z",
                        "proposer": "146ZZqm2cMHLf3ju7oc8M9JnPaAktuADAKThagKnXqzjPJbZ",
                        "error": None
                    }
                ],
                "accountability_analysis": "## Accountability Analysis for Proposal 1679:\n\n**Economic feasibility and cost sharing:** ✅ Clear budget breakdown...\n**Technical implementation:** ⚠️ Needs more technical specifications..."
            }
        }

class GeneralChatResponse(BaseModel):
    ids: List[str] = Field(default=[], description="List of extracted IDs")
    links: List[str] = Field(default=[], description="List of extracted URLs")
    proposals: List[ProposalInfo] = Field(default=[], description="Detailed proposal information for extracted IDs")
    answer: Optional[str] = Field(default=None, description="AI-powered direct answer to the user's question")
    
    class Config:
        json_schema_extra = {
            "example": {
                "ids": ["1679"],
                "links": [],
                "proposals": [
                    {
                        "id": "1679",
                        "title": "CLARYS.AI Beta Product Development",
                        "content": "## Why do we need Clarys.AI?...",
                        "status": "Deciding",
                        "created_at": "2025-07-18T07:26:49.489Z",
                        "proposer": "146ZZqm2cMHLf3ju7oc8M9JnPaAktuADAKThagKnXqzjPJbZ",
                        "error": None
                    }
                ],
                "answer": "Based on the proposal data, the main features of proposal 1679 include..."
            }
        } 