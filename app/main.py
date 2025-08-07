from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from app.models.request_models import ExtractionRequest, EnhancedExtractionRequest
from app.models.response_models import ExtractionResponse, EnhancedExtractionResponse
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
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize the coordinator agent
coordinator = CoordinatorAgent()

@app.get("/")
async def root():
    return {"message": "Multi-Agent ID & Link Extractor API", "version": "1.0.0"}

@app.post("/extract", response_model=ExtractionResponse)
async def extract_ids_and_links(request: ExtractionRequest):
    """
    Extract IDs and links from natural language prompt using multi-agent system
    """
    try:
        logger.info(f"Processing extraction request: {request.prompt}")
        
        # Use coordinator agent to process the request
        result = await coordinator.process_prompt(request.prompt)
        
        logger.info(f"Extraction completed: {result}")
        return result
        
    except Exception as e:
        logger.error(f"Error processing request: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")

@app.post("/extract-with-proposals", response_model=EnhancedExtractionResponse)
async def extract_ids_and_links_with_proposals(request: EnhancedExtractionRequest):
    """
    Extract IDs and links from natural language prompt and fetch detailed proposal information
    """
    try:
        logger.info(f"Processing enhanced extraction request: {request.prompt}")
        
        # Use coordinator agent to process the request with proposal fetching and analysis
        result = await coordinator.process_prompt_with_proposals(
            request.prompt,
            request.proposal_type,
            request.fetch_proposals,
            request.analyze_proposals
        )

        print(f"\n\n\n outcome is {result.proposals} \n \n")
        
        logger.info(f"Enhanced extraction completed: {len(result.ids)} IDs, {len(result.links)} links, {len(result.proposals)} proposals")
        return result
        
    except Exception as e:
        logger.error(f"Error processing enhanced request: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")

@app.get("/health")
async def health_check():
    return {"status": "healthy"} 