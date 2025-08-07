import asyncio
from typing import Dict, Any, List
from app.agents.base_agent import BaseAgent
from app.agents.llm_extractor_agent import LLMExtractorAgent
from app.agents.regex_extractor_agent import RegexExtractorAgent
from app.models.response_models import ExtractionResponse, EnhancedExtractionResponse, ProposalInfo
from app.services.polkadot_api_client import PolkadotAPIClient
from app.services.gemini_analyzer import GeminiAnalyzer

class CoordinatorAgent(BaseAgent):
    """Coordinator agent that orchestrates the LLM and Regex extractor agents"""
    
    def __init__(self):
        super().__init__("Coordinator")
        
        # Initialize the extractor agents
        self.llm_agent = LLMExtractorAgent()
        self.regex_agent = RegexExtractorAgent()
        self.analyzer = GeminiAnalyzer()
    
    async def process_prompt(self, prompt: str) -> ExtractionResponse:
        """Process prompt using both extractor agents and aggregate results"""
        self.log_info(f"Coordinating extraction for prompt: {prompt}")
        
        try:
            # Run both agents in parallel for efficiency
            tasks = [
                self.llm_agent.process(prompt),
                self.regex_agent.process(prompt)
            ]
            
            results = await asyncio.gather(*tasks, return_exceptions=True)
            
            # Process results
            ids = []
            links = []
            
            # Extract IDs from LLM agent result
            if isinstance(results[0], dict) and "ids" in results[0]:
                ids = results[0]["ids"]
            elif isinstance(results[0], Exception):
                self.log_error(f"LLM agent error: {results[0]}")
            
            # Extract links from Regex agent result
            if isinstance(results[1], dict) and "links" in results[1]:
                links = results[1]["links"]
            elif isinstance(results[1], Exception):
                self.log_error(f"Regex agent error: {results[1]}")
            
            # Create response
            response = ExtractionResponse(
                ids=list(set(ids)),  # Remove duplicates
                links=list(set(links))  # Remove duplicates
            )
            
            self.log_info(f"Coordination completed: {response}")
            return response
            
        except Exception as e:
            self.log_error(f"Error in coordination: {str(e)}")
            # Return empty response on error
            return ExtractionResponse(ids=[], links=[])
    
    async def process_prompt_with_proposals(
        self, 
        prompt: str, 
        proposal_type: str = "ReferendumV2",
        fetch_proposals: bool = True,
        analyze_proposals: bool = True
    ) -> EnhancedExtractionResponse:
        """Process prompt and optionally fetch detailed proposal information"""
        self.log_info(f"Enhanced coordinating extraction for prompt: {prompt}")
        
        try:
            # First, extract IDs and links using the standard process
            basic_result = await self.process_prompt(prompt)
            
            proposals = []
            proposal_data_list = []  # Store the fetched data to avoid re-fetching
            
            # If we have IDs and proposal fetching is enabled, fetch proposal details
            if basic_result.ids and fetch_proposals:
                self.log_info(f"Fetching proposal details for {len(basic_result.ids)} IDs")
                
                async with PolkadotAPIClient() as api_client:
                    proposal_data_list = await api_client.fetch_multiple_proposals(
                        basic_result.ids, 
                        proposal_type
                    )
                    
                    # Convert to ProposalInfo objects
                    for proposal_data in proposal_data_list:
                        proposal_info = ProposalInfo(
                            id=proposal_data.id,
                            title=proposal_data.title,
                            content=proposal_data.content,
                            status=proposal_data.status,
                            created_at=proposal_data.created_at,
                            proposer=proposal_data.proposer,
                            beneficiaries=proposal_data.beneficiaries,
                            vote_metrics=proposal_data.vote_metrics,
                            timeline=proposal_data.timeline,
                            error=proposal_data.error
                        )
                        proposals.append(proposal_info)
            
            # Generate AI analysis if requested and we have proposals
            analysis = None
            if analyze_proposals and proposal_data_list:
                self.log_info("Generating AI analysis of proposals")
                try:
                    # Use already fetched proposal data - no need to re-fetch!
                    analysis = await self.analyzer.analyze_proposals(proposal_data_list)
                    self.log_info("AI analysis completed")
                    
                except Exception as e:
                    self.log_error(f"Error generating analysis: {str(e)}")
                    analysis = f"Error generating analysis: {str(e)}"
            
            # Create enhanced response
            enhanced_response = EnhancedExtractionResponse(
                ids=basic_result.ids,
                links=basic_result.links,
                proposals=proposals,
                analysis=analysis
            )
            
            self.log_info(f"Enhanced coordination completed: {len(enhanced_response.ids)} IDs, {len(enhanced_response.links)} links, {len(enhanced_response.proposals)} proposals, analysis: {'Yes' if analysis else 'No'}")
            return enhanced_response
            
        except Exception as e:
            self.log_error(f"Error in enhanced coordination: {str(e)}")
            # Return basic response without proposals on error
            basic_result = await self.process_prompt(prompt)
            return EnhancedExtractionResponse(
                ids=basic_result.ids,
                links=basic_result.links,
                proposals=[],
                analysis=None
            )

    async def process(self, input_data: str) -> Dict[str, Any]:
        """Base agent interface implementation"""
        result = await self.process_prompt(input_data)
        return {
            "ids": result.ids,
            "links": result.links
        } 