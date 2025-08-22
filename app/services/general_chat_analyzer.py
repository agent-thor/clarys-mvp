import os
import asyncio
from typing import List
from google import genai
from app.services.polkadot_api_client import ProposalData
import logging

logger = logging.getLogger(__name__)

class GeneralChatAnalyzer:
    """
    Handles AI-powered general question answering about proposals using the Gemini API.
    Provides direct answers to user questions based on proposal data.
    """
    
    def __init__(self, model_name: str = "gemini-2.5-flash-lite"):
        self.model_name = model_name
        self.client = None
        self._initialize_client()

    def _initialize_client(self):
        """Initializes the Gemini client using the pattern from gemini.py."""
        api_key = os.getenv("GEMINI_API_KEY")
        if not api_key:
            logger.warning("GEMINI_API_KEY not found. GeneralChatAnalyzer will be disabled.")
            return
        
        try:
            # Use genai.Client as seen in gemini.py for consistency
            self.client = genai.Client(api_key=api_key)
            logger.info("Gemini client initialized successfully (general_chat_analyzer).")
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

    async def answer_question_single_proposal(self, proposal: ProposalData, user_question: str) -> str:
        """
        Answers a question about a single proposal using Gemini.
        """
        if hasattr(proposal, 'error') and proposal.error:
            return f"Error: Unable to answer question about proposal {proposal.id} due to a fetch error."

        if not self.client:
            return f"Unable to answer question about proposal {proposal.id}. AI client not available."

        try:
            prompt = f"""
            Below is the data for a proposal and the user's question. Answer the question directly based on the proposal data.

            **User Question:** "{user_question}"

            **Proposal Data:**
            - **ID:** {proposal.id}
            - **Title:** {proposal.title}
            - **Status:** {proposal.status}
            - **Creation Date:** {proposal.created_at[:10] if proposal.created_at else "N/A"}
            - **Proposer:** {proposal.proposer or "Not specified"}
            - **Calculated Reward:** {proposal.calculated_reward or "Not specified"}
            - **Vote Metrics:** {proposal.vote_metrics}
            - **Timeline:** {proposal.timeline}
            - **Content:**
            ---
            {proposal.content}
            ---

            **Instructions:**
            1. Answer the user's question directly and concisely
            2. Base your answer on the proposal data provided above
            3. If the question cannot be answered from the available data, say so clearly
            4. Use a natural, conversational tone
            5. Include specific details from the proposal when relevant
            6. Format your response in clear, readable markdown

            **Answer:**
            """
            
            return await self._safe_gemini_call(prompt)

        except Exception as e:
            logger.error(f"Error answering question for proposal {proposal.id} with Gemini: {str(e)}")
            return f"Error generating answer for proposal {proposal.id}."

    async def answer_question_multiple_proposals(self, proposals: List[ProposalData], user_question: str) -> str:
        """
        Answers a question about multiple proposals using Gemini.
        """
        valid_proposals = [p for p in proposals if not (hasattr(p, 'error') and p.error)]
        if len(valid_proposals) == 0:
            return "No valid proposals available to answer your question."

        if not self.client:
            return "Unable to answer question about proposals. AI client not available."

        try:
            proposal_details = ""
            for i, p in enumerate(valid_proposals, 1):
                proposal_details += f"""
                ---
                **Proposal {i} (ID: {p.id}):**
                - **Title:** {p.title}
                - **Status:** {p.status}
                - **Creation Date:** {p.created_at[:10] if p.created_at else "N/A"}
                - **Proposer:** {p.proposer or "Not specified"}
                - **Calculated Reward:** {p.calculated_reward or "Not specified"}
                - **Vote Metrics:** {p.vote_metrics}
                - **Timeline:** {p.timeline}
                - **Content (first 2000 chars):** {p.content[:2000]}... 
                ---
                """

            prompt = f"""
            Below is the data for {len(valid_proposals)} proposals and the user's question. Answer the question directly based on the proposal data.

            **User Question:** "{user_question}"

            **All Proposal Data:**
            {proposal_details}

            **Instructions:**
            1. Answer the user's question directly and comprehensively
            2. Base your answer on the proposal data provided above
            3. If comparing proposals, highlight key differences and similarities
            4. If the question cannot be answered from the available data, say so clearly
            5. Use a natural, conversational tone
            6. Include specific details from the proposals when relevant
            7. Format your response in clear, readable markdown
            8. If relevant, organize your answer by proposal or by topic

            **Answer:**
            """

            return await self._safe_gemini_call(prompt)

        except Exception as e:
            logger.error(f"Error answering question for multiple proposals with Gemini: {str(e)}")
            return "Error generating answer for the proposals."

    async def analyze_proposals_general_chat(self, proposals: List[ProposalData], user_question: str) -> str:
        """
        Main method to answer questions about proposals.
        Handles 1 or more proposals flexibly.
        """
        if not proposals:
            return "No proposals available to answer your question."
        
        valid_proposals = [p for p in proposals if not (hasattr(p, 'error') and p.error)]
        
        if len(valid_proposals) == 0:
            return "No valid proposals could be found to answer your question."
        elif len(valid_proposals) == 1:
            # Single proposal analysis
            return await self.answer_question_single_proposal(valid_proposals[0], user_question)
        else:
            # Multiple proposal analysis
            return await self.answer_question_multiple_proposals(valid_proposals, user_question)
