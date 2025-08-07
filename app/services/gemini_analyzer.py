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

    async def analyze_single_proposal(self, proposal: ProposalData) -> str:
        """
        Analyzes a single proposal using Gemini to generate and format the output.
        """
        if hasattr(proposal, 'error') and proposal.error:
            return f"Error: Unable to analyze proposal {proposal.id} due to a fetch error."

        if not self.client:
            return f"Proposal {proposal.id}: {proposal.title}\n(AI analysis disabled: Gemini client not available)"

        try:
            prompt = f"""
            Analyze the following proposal and generate a summary in markdown format.

            **Proposal Data:**
            - **ID:** {proposal.id}
            - **Title:** {proposal.title}
            - **Status:** {proposal.status}
            - **Creation Date:** {proposal.created_at[:10] if proposal.created_at else "N/A"}
            - **Proposer:** {proposal.proposer or "Not specified"}
            - **Vote Metrics:** {proposal.vote_metrics}
            - **Timeline:** {proposal.timeline}
            - **Content:**
            ---
            {proposal.content}
            ---

            **Instructions:**
            Generate the output in the following format. The description should be a complete but summarized explanation of the proposal's main goal (around 2-3 sentences). Convert the raw JSON for vote metrics and timeline into a readable, natural language summary.

            **Output Format:**
            ## Proposal {proposal.id}:
            **Title:** {proposal.title}
            **Type:** [Extract from content, e.g., ReferendumV2, Child Bounty]
            **Proposer:** [Proposer Address]
            **Reward:** [Extract reward amount and currency, e.g., "256,096 USDC" or "460.7 DOT". If not found, state "Not specified"]
            **Category:** [Extract from content, e.g., Development, Marketing, Infrastructure]
            **Status:** {proposal.status}
            **Creation Date:** {proposal.created_at[:10] if proposal.created_at else "N/A"}
            **Description:** [A complete but summarized description of the proposal's main goal. ~2-3 sentences]
            **Voting Status:** [Natural language summary of vote_metrics, e.g., "12 Aye votes, 35 Nay votes, 0.7 DOT in support"]
            **Timeline:** [Natural language summary of timeline, e.g., "Submitted on 2025-07-18 → Deciding on 2025-07-18"]
            """
            
            return await self._safe_gemini_call(prompt)

        except Exception as e:
            logger.error(f"Error analyzing single proposal {proposal.id} with Gemini: {str(e)}")
            return f"Error generating analysis for proposal {proposal.id}."

    async def compare_proposals(self, proposals: List[ProposalData]) -> str:
        """
        Compares multiple proposals using Gemini to generate and format the entire output.
        """
        valid_proposals = [p for p in proposals if not (hasattr(p, 'error') and p.error)]
        if len(valid_proposals) < 2:
            return "Error: Not enough valid proposals to compare."

        if not self.client:
            return "Could not generate comparison. AI client not available."

        try:
            proposal_details = ""
            for p in valid_proposals:
                proposal_details += f"""
                ---
                **Proposal Data (ID: {p.id}):**
                - **Title:** {p.title}
                - **Status:** {p.status}
                - **Creation Date:** {p.created_at[:10] if p.created_at else "N/A"}
                - **Proposer:** {p.proposer or "Not specified"}
                - **Vote Metrics:** {p.vote_metrics}
                - **Timeline:** {p.timeline}
                - **Content (first 2000 chars):** {p.content[:2000]}... 
                ---
                """

            prompt = f"""
            Analyze and compare the following proposals. Generate a detailed summary for each, followed by a final comparison section, all in markdown format.

            **All Proposal Data:**
            {proposal_details}

            **Instructions:**
            1.  For EACH proposal, create a summary section as specified in the format below.
            2.  After all individual summaries, create a "## Comparison" section.
            3.  The description for each proposal must be a complete but summarized explanation of its purpose (~2-3 sentences).
            4.  Convert raw JSON data for votes and timeline into readable, natural language summaries.
            5.  The final comparison section must be concise (1 sentence per point).

            **Required Output Format:**

            ## Proposal [ID]:
            **Title:** [Title]
            **Type:** [Extract from content, e.g., ReferendumV2]
            **Proposer:** [Proposer Address]
            **Reward:** [Extract reward amount and currency. If not found, state "Not specified"]
            **Category:** [Extract from content, e.g., Development]
            **Status:** [Status]
            **Creation Date:** [Creation Date]
            **Description:** [A complete but summarized description. ~2-3 sentences]
            **Voting Status:** [Natural language summary of votes]
            **Timeline:** [Natural language summary of timeline]

            ## Proposal [Next ID]:
            ... (repeat for each proposal) ...

            ## Comparison:
            **Cost:** [Compare funding amounts in 1 sentence]
            **Milestones:** [Compare timelines and deliverables in 1 sentence]
            **Impact on Polkadot:** [Compare ecosystem impact in 1 sentence]
            **Timeline:** [Compare project timelines in 1 sentence]
            **Completeness:** [Compare how well-defined each proposal is in 1 sentence]
            """

            return await self._safe_gemini_call(prompt)

        except Exception as e:
            logger.error(f"Error comparing proposals with Gemini: {str(e)}")
            return "Error generating proposal comparison."

    async def analyze_proposals(self, proposals: List[ProposalData]) -> str:
        """
        Main method to analyze proposals. It delegates to the appropriate
        single or comparison method based on the number of valid proposals.
        """
        if not proposals:
            return "No proposals to analyze."
        
        valid_proposals = [p for p in proposals if not (hasattr(p, 'error') and p.error)]
        
        if len(valid_proposals) == 0:
            return "No valid proposals could be analyzed."
        elif len(valid_proposals) == 1:
            return await self.analyze_single_proposal(valid_proposals[0])
        else:
            return await self.compare_proposals(valid_proposals) 