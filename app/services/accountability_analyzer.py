import os
import asyncio
from typing import List
from google import genai
from app.services.polkadot_api_client import ProposalData
import logging

logger = logging.getLogger(__name__)

class AccountabilityAnalyzer:
    """
    Handles AI-powered accountability analysis of proposals using the Gemini API.
    Focuses on governance accountability checkpoints.
    """
    
    def __init__(self, model_name: str = "gemini-2.5-flash-lite"):
        self.model_name = model_name
        self.client = None
        self._initialize_client()
        
        # Define accountability checkpoints
        self.accountability_checkpoints = [
            "Economic feasibility and cost sharing",
            "Technical implementation and specifications", 
            "Governance approvals and inter-ecosystem agreements",
            "Storage token decision and neutrality",
            "Strategic benefit delivery",
            "Validator set and security model",
            "Public communication and stakeholder engagement"
        ]

    def _initialize_client(self):
        """Initializes the Gemini client using the pattern from gemini.py."""
        api_key = os.getenv("GEMINI_API_KEY")
        if not api_key:
            logger.warning("GEMINI_API_KEY not found. AccountabilityAnalyzer will be disabled.")
            return
        
        try:
            # Use genai.Client as seen in gemini.py for consistency
            self.client = genai.Client(api_key=api_key)
            logger.info("Gemini client initialized successfully (accountability_analyzer).")
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

    async def analyze_single_proposal_accountability(self, proposal: ProposalData) -> str:
        """
        Analyzes a single proposal for accountability using Gemini.
        """
        if hasattr(proposal, 'error') and proposal.error:
            return f"Error: Unable to analyze proposal {proposal.id} due to a fetch error."

        if not self.client:
            return f"Proposal {proposal.id}: {proposal.title}\n(AI analysis disabled: Gemini client not available)"

        try:
            checkpoints_text = "\n".join([f"- {checkpoint}" for checkpoint in self.accountability_checkpoints])
            
            prompt = f"""
            Perform an accountability analysis of the following proposal based on governance best practices.

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
            Analyze this proposal against the following accountability checkpoints. For each checkpoint, provide:
            1. A status indicator: ✅ (Strong), ⚠️ (Moderate), ❌ (Weak/Missing)
            2. A brief 1-2 sentence assessment explaining your rating

            **Accountability Checkpoints:**
            {checkpoints_text}

            **Output Format:**
            ## Accountability Analysis for Proposal {proposal.id}:

            **Proposal Overview:**
            - **Title:** {proposal.title}
            - **Type:** [Extract from content]
            - **Reward:** {proposal.calculated_reward or "Not specified"}
            - **Status:** {proposal.status}

            **Accountability Assessment:**

            **Economic feasibility and cost sharing:** [✅/⚠️/❌] [Assessment in 1-2 sentences]

            **Technical implementation and specifications:** [✅/⚠️/❌] [Assessment in 1-2 sentences]

            **Governance approvals and inter-ecosystem agreements:** [✅/⚠️/❌] [Assessment in 1-2 sentences]

            **Storage token decision and neutrality:** [✅/⚠️/❌] [Assessment in 1-2 sentences]

            **Strategic benefit delivery:** [✅/⚠️/❌] [Assessment in 1-2 sentences]

            **Validator set and security model:** [✅/⚠️/❌] [Assessment in 1-2 sentences]

            **Public communication and stakeholder engagement:** [✅/⚠️/❌] [Assessment in 1-2 sentences]

            **Overall Accountability Score:** [X/7] checkpoints met with strong accountability measures.

            **Questions to answer:**
            -When is the project successful?

            -By when is the final delivery of the project expected?

            -Details of the beneficiary:

            -Which audience is targeted in this proposal?

            -How will success be measured?

            -What is the (measurable) benefit for Polkadot?

            -Are deliverables clearly specified?

            -What are the funds used for in this proposal?
            """
            
            return await self._safe_gemini_call(prompt)

        except Exception as e:
            logger.error(f"Error analyzing accountability for proposal {proposal.id} with Gemini: {str(e)}")
            return f"Error generating accountability analysis for proposal {proposal.id}."

    async def compare_proposals_accountability(self, proposals: List[ProposalData]) -> str:
        """
        Compares multiple proposals for accountability using Gemini.
        Can handle 2, 3, or more proposals.
        """
        valid_proposals = [p for p in proposals if not (hasattr(p, 'error') and p.error)]
        if len(valid_proposals) < 2:
            # If less than 2 proposals, treat as single analysis
            return await self.analyze_single_proposal_accountability(valid_proposals[0]) if valid_proposals else "No valid proposals to analyze."

        if not self.client:
            return "Could not generate accountability comparison. AI client not available."

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
                - **Calculated Reward:** {p.calculated_reward or "Not specified"}
                - **Vote Metrics:** {p.vote_metrics}
                - **Timeline:** {p.timeline}
                - **Content (first 2000 chars):** {p.content[:2000]}... 
                ---
                """

            checkpoints_text = "\n".join([f"- {checkpoint}" for checkpoint in self.accountability_checkpoints])
            
            # Create proposal list for summary
            proposal_ids = [p.id for p in valid_proposals]
            proposal_list = ", ".join(proposal_ids[:-1]) + f" and {proposal_ids[-1]}" if len(proposal_ids) > 1 else proposal_ids[0]

            prompt = f"""
            Perform a comparative accountability analysis of the following {len(valid_proposals)} proposals based on governance best practices.

            **All Proposal Data:**
            {proposal_details}

            **Instructions:**
            1. For EACH proposal, provide an accountability assessment against the checkpoints below
            2. After individual assessments, provide a comparative summary
            3. Use status indicators: ✅ (Strong), ⚠️ (Moderate), ❌ (Weak/Missing)
            4. Be thorough in analyzing each proposal individually before comparing

            **Accountability Checkpoints:**
            {checkpoints_text}

            **Required Output Format:**

            ## Accountability Analysis for Proposal [ID]:

            **Proposal Overview:**
            - **Title:** [Title]
            - **Type:** [Extract from content]
            - **Reward:** [Use calculated reward]
            - **Status:** [Status]

            **Accountability Assessment:**
            **Economic feasibility and cost sharing:** [✅/⚠️/❌] [Assessment]
            **Technical implementation and specifications:** [✅/⚠️/❌] [Assessment]
            **Governance approvals and inter-ecosystem agreements:** [✅/⚠️/❌] [Assessment]
            **Storage token decision and neutrality:** [✅/⚠️/❌] [Assessment]
            **Strategic benefit delivery:** [✅/⚠️/❌] [Assessment]
            **Validator set and security model:** [✅/⚠️/❌] [Assessment]
            **Public communication and stakeholder engagement:** [✅/⚠️/❌] [Assessment]

            **Overall Accountability Score:** [X/7]

            [Repeat the above format for each of the {len(valid_proposals)} proposals]

            **Questions to answer:**
            -When is the project successful?
            -By when is the final delivery of the project expected?
            -Details of the beneficiary:
            -Which audience is targeted in this proposal?
            -How will success be measured?
            -What is the (measurable) benefit for Polkadot?
            -Are deliverables clearly specified?
            -What are the funds used for in this proposal?

            ## Comparative Accountability Summary:
            **Most Accountable:** Proposal [ID] with [X/7] strong checkpoints
            **Accountability Ranking:** [Rank all {len(valid_proposals)} proposals from most to least accountable]
            **Key Differences:** [Brief comparison of accountability strengths/weaknesses across all proposals]
            **Common Weaknesses:** [Areas where multiple proposals could improve accountability]
            **Recommendations:** [Specific suggestions for improving accountability in weaker proposals]
            """

            return await self._safe_gemini_call(prompt)

        except Exception as e:
            logger.error(f"Error comparing proposals accountability with Gemini: {str(e)}")
            return "Error generating accountability comparison."

    async def analyze_proposals_accountability(self, proposals: List[ProposalData]) -> str:
        """
        Main method to analyze proposals for accountability.
        Handles 1, 2, 3, or more proposals flexibly.
        """
        if not proposals:
            return "No proposals to analyze for accountability."
        
        valid_proposals = [p for p in proposals if not (hasattr(p, 'error') and p.error)]
        
        if len(valid_proposals) == 0:
            return "No valid proposals could be analyzed for accountability."
        elif len(valid_proposals) == 1:
            # Single proposal analysis
            return await self.analyze_single_proposal_accountability(valid_proposals[0])
        else:
            # Multiple proposal comparison (2, 3, or more)
            return await self.compare_proposals_accountability(valid_proposals) 