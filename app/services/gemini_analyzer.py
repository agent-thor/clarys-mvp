import os
import asyncio
from typing import List
from google import genai
from app.services.polkadot_api_client import ProposalData
import logging

logger = logging.getLogger(__name__)

class GeminiAnalyzer:
    """
    Handles AI-powered analysis and comparison of proposals using the Gemini API.
    This class is configured to align with the client pattern in gemini.py.
    """
    
    def __init__(self, model_name: str = "gemini-2.5-flash-lite"):
        self.model_name = model_name
        self.client = None
        self._initialize_client()

    def _initialize_client(self):
        """Initializes the Gemini client using the pattern from gemini.py."""
        api_key = os.getenv("GEMINI_API_KEY")
        if not api_key:
            logger.warning("GEMINI_API_KEY not found. GeminiAnalyzer will be disabled.")
            return
        
        try:
            # Use genai.Client as seen in gemini.py for consistency
            self.client = genai.Client(api_key=api_key)
            logger.info("Gemini client initialized successfully (gemini_analyzer).")
        except Exception as e:
            logger.error(f"Failed to initialize Gemini client: {str(e)}")
            self.client = None

    async def _safe_gemini_call(self, prompt: str) -> str:
        """
        Awaits the Gemini API call in a separate thread to avoid blocking
        the async event loop.
        """
        loop = asyncio.get_event_loop()
        response = await loop.run_in_executor(
            None,
            lambda: self.client.models.generate_content(
                model=self.model_name,
                contents=prompt
            )
        )
        return response.text.strip()

    async def analyze_single_proposal(self, proposal: ProposalData, custom_prompt: str = None) -> str:
        """
        Analyzes a single proposal using Gemini.
        
        Args:
            proposal: The proposal data to analyze
            custom_prompt: Optional custom prompt to use instead of the default
            
        Returns:
            AI-generated analysis of the proposal
        """
        if not self.client:
            return "Could not generate analysis. AI client not available."
        
        try:
            if custom_prompt:
                # Use the custom prompt directly
                response = await self._safe_gemini_call(custom_prompt)
                return response
            else:
                # Use the default analysis prompt
                prompt = f"""
                Analyze this Polkadot governance proposal and provide a detailed summary in the following format:

                ## {proposal.title}

                **Type:** {proposal.proposal_type}
                **Proposer:** {proposal.proposer}
                **Reward:** {proposal.calculated_reward}
                **Category:** [Extract from content]
                **Status:** {proposal.status}
                **Creation Date:** {proposal.created_at}

                **Description:** [Provide a concise 2-3 sentence summary of what this proposal is about]

                **Voting Status:** [Convert the following vote metrics to natural language with proper markdown: {proposal.vote_metrics}]

                **Timeline:** [Convert the following timeline to natural language with proper markdown: {proposal.timeline}]

                Here is the full proposal data:
                {proposal.content}

                Important guidelines:
                - Keep descriptions concise and focused
                - Convert all JSON data (votes, timeline) to natural language with markdown formatting
                - Extract reward amount from beneficiaries data: {proposal.beneficiaries}
                - Focus on key information that helps understand the proposal's purpose and current status
                """
                
                response = await self._safe_gemini_call(prompt)
                return response
                
        except Exception as e:
            logger.error(f"Error in analyze_single_proposal: {str(e)}")
            return f"Could not generate analysis. Error: {str(e)}"

    async def compare_proposals(self, proposals: List[ProposalData], custom_prompt: str = None) -> str:
        """
        Compares multiple proposals using Gemini.
        
        Args:
            proposals: List of proposal data to compare
            custom_prompt: Optional custom prompt to use instead of the default
            
        Returns:
            AI-generated comparison of the proposals
        """
        if not self.client:
            return "Could not generate comparison. AI client not available."
        
        if len(proposals) < 2:
            if len(proposals) == 1:
                return await self.analyze_single_proposal(proposals[0], custom_prompt)
            return "Cannot compare proposals. At least 2 proposals are required."
        
        try:
            if custom_prompt:
                # Use the custom prompt directly
                response = await self._safe_gemini_call(custom_prompt)
                return response
            else:
                # Use the default comparison prompt
                individual_summaries = []
                for i, proposal in enumerate(proposals, 1):
                    summary = f"""
                    **Proposal {i}: {proposal.title}**
                    - **Type:** {proposal.proposal_type}
                    - **Proposer:** {proposal.proposer}
                    - **Reward:** {proposal.calculated_reward}
                    - **Category:** [Extract from content]
                    - **Status:** {proposal.status}
                    - **Creation Date:** {proposal.created_at}
                    - **Description:** [Provide a concise summary]
                    - **Voting Status:** [Convert to natural language: {proposal.vote_metrics}]
                    - **Timeline:** [Convert to natural language: {proposal.timeline}]
                    
                    Full content: {proposal.content}
                    """
                    individual_summaries.append(summary)
                
                prompt = f"""
                Compare these {len(proposals)} Polkadot governance proposals and provide analysis in the following format:

                {chr(10).join(individual_summaries)}

                ## Comparison

                **Cost:** [Compare the reward amounts and financial implications]

                **Milestones:** [Compare the timelines, milestones, and deliverables]

                **Impact on Polkadot:** [Compare the potential impact on the Polkadot ecosystem]

                **Timeline:** [Compare the proposed timelines and urgency]

                **Completeness:** [Compare how well-defined and detailed each proposal is]

                Important guidelines:
                - Provide concise, focused analysis
                - Convert all JSON data to natural language with markdown formatting
                - Focus on key differences and similarities
                - Use the calculated_reward field for accurate reward information
                """
                
                response = await self._safe_gemini_call(prompt)
                return response
                
        except Exception as e:
            logger.error(f"Error in compare_proposals: {str(e)}")
            return f"Could not generate comparison. Error: {str(e)}"

    async def analyze_proposals(self, proposals: List[ProposalData]) -> str:
        """
        Main method to analyze proposals. It delegates to the appropriate
        single or comparison method based on the number of valid proposals.
        Requires at least 2 proposals for comparison analysis.
        """
        if not proposals:
            return "No proposals to analyze."
        
        valid_proposals = [p for p in proposals if not (hasattr(p, 'error') and p.error)]
        
        if len(valid_proposals) == 0:
            return "No valid proposals could be analyzed."
        elif len(valid_proposals) == 1:
            return await self.analyze_single_proposal(valid_proposals[0])
        else:
            # Only proceed with comparison if we have at least 2 proposals
            return await self.compare_proposals(valid_proposals) 