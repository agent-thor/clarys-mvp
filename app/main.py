from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from app.models.request_models import ExtractionRequest, EnhancedExtractionRequest, AccountabilityCheckRequest, GeneralChatRequest
from app.models.response_models import ExtractionResponse, EnhancedExtractionResponse, AccountabilityCheckResponse, GeneralChatResponse
from app.services.coordinator_agent import CoordinatorAgent
from app.services.routing_service import RoutingService
from app.services.algolia import PolkassemblySearch
from app.services.database import database_service
from app.services.rate_limiter import rate_limiter
from pydantic import BaseModel
import logging
import time
import json
import os
from typing import Dict, Any

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(
    title="Multi-Agent ID & Link Extractor API",
    description="API that uses multi-agent system to extract IDs and links from natural language prompts",
    version="1.0.0"
)

@app.on_event("startup")
async def startup_event():
    """Initialize database connection on startup"""
    try:
        await database_service.initialize()
        logger.info("Database initialized successfully")
    except Exception as e:
        logger.error(f"Failed to initialize database: {str(e)}")
        # Don't raise exception to allow API to start even if database is unavailable

@app.on_event("shutdown")
async def shutdown_event():
    """Close database connections on shutdown"""
    try:
        await database_service.close()
        logger.info("Database connections closed")
    except Exception as e:
        logger.error(f"Error closing database connections: {str(e)}")

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

async def check_rate_limit_and_log(user_email: str, endpoint: str) -> int:
    """
    Check rate limit for user and return remaining requests.
    Raises HTTPException if rate limit exceeded.
    """
    logger.info(f"🚦 Checking rate limit for {user_email} on endpoint {endpoint}")
    is_allowed, remaining = await rate_limiter.check_rate_limit(user_email)
    logger.info(f"🚦 Rate limit result: allowed={is_allowed}, remaining={remaining}")
    
    if not is_allowed:
        logger.warning(f"Rate limit exceeded for user {user_email} on endpoint {endpoint}")
        raise HTTPException(
            status_code=429, 
            detail={
                "error": "Rate limit exceeded",
                "message": f"You have exceeded the limit of {rate_limiter.requests_per_window} requests per {rate_limiter.window_hours} hours",
                "remaining_requests": remaining
            }
        )
    
    return remaining

async def log_query_result(
    user_email: str, 
    endpoint: str, 
    prompt: str, 
    result: dict, 
    success: bool = True,
    error_message: str = None,
    start_time: float = None
):
    """Log query result to database"""
    processing_time_ms = None
    if start_time:
        processing_time_ms = int((time.time() - start_time) * 1000)
    
    await rate_limiter.log_query(
        user_email=user_email,
        endpoint=endpoint,
        prompt=prompt,
        result=result if success else None,
        success=success,
        error_message=error_message,
        processing_time_ms=processing_time_ms
    )

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
            "/general-chat": "General question answering about proposals",
            "/route": "Intelligent prompt routing",
            "/search-and-analyze": "Search Algolia and analyze with Gemini",
            "/initiate": "Get all stored conversations from conversations.json",
            "/health": "Health check"
        }
    }

@app.post("/extract", response_model=ExtractionResponse)
async def extract_ids_and_links(request: ExtractionRequest):
    """Basic extraction of IDs and links from prompt"""
    start_time = time.time()
    
    try:
        # Check rate limit
        remaining = await check_rate_limit_and_log(request.user_email, "extract")
        
        # Process request
        result = await coordinator.process_prompt(request.prompt)
        
        # Add remaining requests to response
        response_data = {
            "ids": result.ids,
            "links": result.links,
            "remaining_requests": remaining
        }
        response = ExtractionResponse(**response_data)
        
        # Log successful query
        await log_query_result(
            user_email=request.user_email,
            endpoint="extract",
            prompt=request.prompt,
            result=response_data,
            success=True,
            start_time=start_time
        )
        
        return response
        
    except HTTPException:
        # Re-raise HTTP exceptions (like rate limit exceeded)
        raise
    except Exception as e:
        # Log failed query
        await log_query_result(
            user_email=request.user_email,
            endpoint="extract",
            prompt=request.prompt,
            result=None,
            success=False,
            error_message=str(e),
            start_time=start_time
        )
        
        logger.error(f"Error in /extract: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/extract-with-proposals", response_model=EnhancedExtractionResponse)
async def extract_with_proposals(request: EnhancedExtractionRequest):
    """Enhanced extraction with proposal fetching and AI analysis"""
    start_time = time.time()
    
    try:
        # Check rate limit
        remaining = await check_rate_limit_and_log(request.user_email, "extract-with-proposals")
        
        # Process request
        result = await coordinator.process_prompt_with_proposals(request.prompt, remaining_requests=remaining)
        print(result)

        # Convert to dict for logging
        response_data = result.model_dump()
        
        # Log successful query
        await log_query_result(
            user_email=request.user_email,
            endpoint="extract-with-proposals",
            prompt=request.prompt,
            result=response_data,
            success=True,
            start_time=start_time
        )
        
        return result
        
    except HTTPException:
        # Re-raise HTTP exceptions (like rate limit exceeded)
        raise
    except Exception as e:
        # Log failed query
        await log_query_result(
            user_email=request.user_email,
            endpoint="extract-with-proposals",
            prompt=request.prompt,
            result=None,
            success=False,
            error_message=str(e),
            start_time=start_time
        )
        
        logger.error(f"Error in /extract-with-proposals: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/accountability-check", response_model=AccountabilityCheckResponse)
async def accountability_check(request: AccountabilityCheckRequest):
    """Accountability analysis of proposals"""
    start_time = time.time()
    
    try:
        # Check rate limit
        remaining = await check_rate_limit_and_log(request.user_email, "accountability-check")
        
        # Process request
        result = await coordinator.process_prompt_with_accountability_check(request.prompt, remaining_requests=remaining)
        
        # Convert to dict for logging
        response_data = result.model_dump()
        
        # Log successful query
        await log_query_result(
            user_email=request.user_email,
            endpoint="accountability-check",
            prompt=request.prompt,
            result=response_data,
            success=True,
            start_time=start_time
        )
        
        return result
        
    except HTTPException:
        # Re-raise HTTP exceptions (like rate limit exceeded)
        raise
    except Exception as e:
        # Log failed query
        await log_query_result(
            user_email=request.user_email,
            endpoint="accountability-check",
            prompt=request.prompt,
            result=None,
            success=False,
            error_message=str(e),
            start_time=start_time
        )
        
        logger.error(f"Error in /accountability-check: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/general-chat", response_model=GeneralChatResponse)
async def general_chat(request: GeneralChatRequest):
    """General question answering about proposals"""
    start_time = time.time()
    
    try:
        # Check rate limit
        remaining = await check_rate_limit_and_log(request.user_email, "general-chat")
        
        # Process request
        result = await coordinator.process_prompt_with_general_chat(request.prompt, remaining_requests=remaining)
        
        # Convert to dict for logging
        response_data = result.model_dump()
        
        # Log successful query
        await log_query_result(
            user_email=request.user_email,
            endpoint="general-chat",
            prompt=request.prompt,
            result=response_data,
            success=True,
            start_time=start_time
        )
        
        return result
        
    except HTTPException:
        # Re-raise HTTP exceptions (like rate limit exceeded)
        raise
    except Exception as e:
        # Log failed query
        await log_query_result(
            user_email=request.user_email,
            endpoint="general-chat",
            prompt=request.prompt,
            result=None,
            success=False,
            error_message=str(e),
            start_time=start_time
        )
        
        logger.error(f"Error in /general-chat: {str(e)}")
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

@app.get("/initiate")
async def get_conversations():
    """
    Get all stored conversations from conversations.json
    
    Returns:
        Dict containing all stored conversations organized by endpoint
    """
    try:
        # Path to conversations.json file
        conversations_file = os.path.join(os.path.dirname(__file__), '..', 'data', 'conversations.json')
        
        # Check if file exists
        if not os.path.exists(conversations_file):
            return {
                "message": "No conversations found",
                "conversations": {}
            }
        
        # Read and return the conversations file
        with open(conversations_file, 'r', encoding='utf-8') as f:
            conversations = json.load(f)
        
        return {
            "message": "Conversations retrieved successfully",
            "total_conversations": sum(len(convs) for convs in conversations.values()),
            "endpoints": list(conversations.keys()),
            "conversations": conversations
        }
        
    except json.JSONDecodeError as e:
        logger.error(f"Error parsing conversations.json: {str(e)}")
        raise HTTPException(
            status_code=500, 
            detail="Error parsing conversations file"
        )
    except Exception as e:
        logger.error(f"Error reading conversations: {str(e)}")
        raise HTTPException(
            status_code=500, 
            detail="Error retrieving conversations"
        )

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