from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from app.models.request_models import ExtractionRequest, EnhancedExtractionRequest, AccountabilityCheckRequest
from app.models.response_models import ExtractionResponse, EnhancedExtractionResponse, AccountabilityCheckResponse
from app.services.coordinator_agent import CoordinatorAgent
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
    allow_origins=["*"],  # In production, replace with specific origins
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize the coordinator agent
coordinator = CoordinatorAgent()

@app.get("/")
async def root():
    return {
        "message": "Multi-Agent ID & Link Extractor API",
        "version": "1.0.0",
        "endpoints": {
            "/extract": "Basic ID and link extraction",
            "/extract-with-proposals": "Enhanced extraction with proposal fetching and AI analysis",
            "/accountability-check": "Accountability analysis of proposals based on governance checkpoints"
        }
    }

@app.get("/health")
async def health_check():
    return {"status": "healthy", "message": "API is running"}

@app.post("/extract", response_model=ExtractionResponse)
async def extract_ids_and_links(request: ExtractionRequest):
    """
    Extract IDs and links from natural language prompt using multi-agent system
    """
    try:
        logger.info(f"Processing extraction request: {request.prompt}")
        
        # Use coordinator agent to process the request
        result = await coordinator.process_prompt(request.prompt)
        
        logger.info(f"Extraction completed: {len(result.ids)} IDs, {len(result.links)} links")
        return result
        
    except Exception as e:
        logger.error(f"Error processing request: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")

@app.post("/extract-with-proposals", response_model=EnhancedExtractionResponse)
async def extract_ids_and_links_with_proposals(request: EnhancedExtractionRequest):
    """
    Extracts IDs and links, fetches proposal data, and returns an AI analysis.
    The proposal type is intelligently determined from the prompt.
    """
    try:
        logger.info(f"Processing enhanced extraction request: {request.prompt}")
        
        # The coordinator now handles all logic internally
        result = await coordinator.process_prompt_with_proposals(request.prompt)
        
        logger.info(f"Enhanced extraction completed: {len(result.ids)} IDs, {len(result.links)} links, {len(result.proposals)} proposals, analysis: {'Yes' if result.analysis else 'No'}")
        return result
        
    except Exception as e:
        logger.error(f"Error processing enhanced request: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")

@app.post("/accountability-check", response_model=AccountabilityCheckResponse)
async def accountability_check_proposals(request: AccountabilityCheckRequest):
    """
    Extracts IDs and links, fetches proposal data, and returns an AI-powered accountability analysis
    based on governance best practices and key accountability checkpoints.
    """
    try:
        logger.info(f"Processing accountability check request: {request.prompt}")
        
        # Use coordinator agent to process the request with accountability analysis
        result = await coordinator.process_prompt_with_accountability_check(request.prompt)
        
        logger.info(f"Accountability check completed: {len(result.ids)} IDs, {len(result.links)} links, {len(result.proposals)} proposals, analysis: {'Yes' if result.accountability_analysis else 'No'}")
        return result
        
    except Exception as e:
        logger.error(f"Error processing accountability check request: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000) 