from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from app.models.request_models import ExtractionRequest, EnhancedExtractionRequest, AccountabilityCheckRequest
from app.models.response_models import ExtractionResponse, EnhancedExtractionResponse, AccountabilityCheckResponse
from app.services.coordinator_agent import CoordinatorAgent
from app.services.routing_service import RoutingService
from app.services.algolia import PolkassemblySearch
from pydantic import BaseModel
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(
    title="Multi-Agent ID & Link Extractor API",
    description="API that uses multi-agent system to extract IDs and links from natural language prompts",
    version="1.0.0"
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize services
coordinator = CoordinatorAgent()
routing_service = RoutingService()
algolia_client = PolkassemblySearch()

class SearchAnalyzeRequest(BaseModel):
    """Request model for search and analyze endpoint"""
    query: str
    num_results: int = 5

class SearchAnalyzeResponse(BaseModel):
    """Response model for search and analyze endpoint"""
    query: str
    algolia_results: list
    proposals: list
    analysis: str

@app.get("/")
async def root():
    """Root endpoint with API information"""
    return {
        "message": "Multi-Agent ID & Link Extractor API",
        "version": "1.0.0",
        "endpoints": {
            "/extract": "Basic ID and link extraction",
            "/extract-with-proposals": "Enhanced extraction with proposal fetching and AI analysis",
            "/accountability-check": "Accountability analysis of proposals",
            "/route": "Intelligent prompt routing",
            "/search-and-analyze": "Search Algolia and analyze with Gemini",
            "/health": "Health check"
        }
    }

@app.post("/extract", response_model=ExtractionResponse)
async def extract_ids_and_links(request: ExtractionRequest):
    """Basic extraction of IDs and links from prompt"""
    try:
        result = await coordinator.process_prompt(request.prompt)
        return ExtractionResponse(**result)
    except Exception as e:
        logger.error(f"Error in /extract: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/extract-with-proposals", response_model=EnhancedExtractionResponse)
async def extract_with_proposals(request: EnhancedExtractionRequest):
    """Enhanced extraction with proposal fetching and AI analysis"""
    try:
        result = await coordinator.process_prompt_with_proposals(request.prompt)
        return result  # Return directly, don't unpack with **
    except Exception as e:
        logger.error(f"Error in /extract-with-proposals: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/accountability-check", response_model=AccountabilityCheckResponse)
async def accountability_check(request: AccountabilityCheckRequest):
    """Accountability analysis of proposals"""
    try:
        result = await coordinator.process_prompt_with_accountability_check(request.prompt)
        return result  # Return directly, don't unpack with **
    except Exception as e:
        logger.error(f"Error in /accountability-check: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/route")
async def route_request(request: dict):
    """Intelligent prompt routing"""
    try:
        prompt = request.get("prompt", "")
        if not prompt:
            raise HTTPException(status_code=400, detail="Prompt is required")
        
        result = await routing_service.process_routed_request(prompt)
        return result
    except Exception as e:
        logger.error(f"Error in /route: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/search-and-analyze", response_model=SearchAnalyzeResponse)
async def search_and_analyze(request: SearchAnalyzeRequest):
    """
    Complete workflow: Search Algolia -> Extract proposal IDs/types -> Fetch from Polkassembly -> Analyze with Gemini
    
    This endpoint:
    1. Searches Algolia for relevant proposals based on the query
    2. Extracts proposal IDs and types (ReferendumV2 or Discussion) from search results
    3. Fetches detailed proposal data from Polkassembly API
    4. Sends the data to Gemini for intelligent analysis and query answering
    """
    try:
        logger.info(f"Processing search and analyze request for query: '{request.query}'")
        
        result = await algolia_client.search_and_analyze_with_gemini(
            request.query, 
            request.num_results
        )
        
        return SearchAnalyzeResponse(**result)
        
    except Exception as e:
        logger.error(f"Error in /search-and-analyze: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "message": "Multi-Agent API is running",
        "services": {
            "coordinator": "active",
            "routing_service": "active",
            "algolia_client": "active"
        }
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000) 