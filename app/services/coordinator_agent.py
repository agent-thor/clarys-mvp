import asyncio
import re
from typing import Dict, Any, List, Tuple, Optional
from app.agents.base_agent import BaseAgent
from app.agents.llm_extractor_agent import LLMExtractorAgent
from app.agents.regex_extractor_agent import RegexExtractorAgent
from app.models.response_models import ExtractionResponse, EnhancedExtractionResponse, ProposalInfo, AccountabilityCheckResponse
from app.services.polkadot_api_client import PolkadotAPIClient, ProposalData
from app.services.gemini_analyzer import GeminiAnalyzer
from app.services.accountability_analyzer import AccountabilityAnalyzer

class CoordinatorAgent(BaseAgent):
    def __init__(self):
        super().__init__("Coordinator")
        self.llm_agent = LLMExtractorAgent()
        self.regex_agent = RegexExtractorAgent()
        self.analyzer = GeminiAnalyzer()
        self.accountability_analyzer = AccountabilityAnalyzer()

    def _parse_links(self, links: List[str]) -> List[Tuple[str, str]]:
        """
        Parses URLs to extract the proposal ID and type ('Discussion' or 'ReferendumV2').
        Example 1: .../referenda/1697 -> ("1697", "ReferendumV2")
        Example 2: .../post/3313 -> ("3313", "Discussion")
        """
        parsed_proposals = []
        # Pattern to capture type ('referenda' or 'post') and the trailing ID
        pattern = r"/(referenda|post)/(\d+)$"
        
        for link in links:
            match = re.search(pattern, link)
            if match:
                type_str, p_id = match.groups()
                proposal_type = "ReferendumV2" if type_str == "referenda" else "Discussion"
                parsed_proposals.append((p_id, proposal_type))
        
        return parsed_proposals

    def _calculate_reward(self, proposal: ProposalData) -> Optional[str]:
        """Calculates the total reward from the beneficiaries list."""
        if not proposal.beneficiaries:
            return None
        
        total_amount = 0
        currency = "tokens"  # Default currency
        
        for beneficiary in proposal.beneficiaries:
            try:
                amount = int(beneficiary.get("amount", 0))
                asset_id = beneficiary.get("assetId")

                if asset_id == "1337":  # Assume USDC
                    total_amount += amount / 1_000_000  # 6 decimals for USDC
                    currency = "USDC"
                else:  # Assume DOT or other 10-decimal tokens
                    total_amount += amount / 10_000_000_000
                    currency = "DOT"
            except (ValueError, TypeError):
                continue # Skip if amount is not a valid number
        
        if total_amount > 0:
            return f"{total_amount:,.2f} {currency}"
        return None

    async def process_prompt_with_proposals(self, prompt: str) -> EnhancedExtractionResponse:
        """
        Processes a prompt to extract IDs and links, intelligently determines proposal types,
        fetches data, calculates rewards, and generates an AI analysis.
        """
        self.log_info(f"Enhanced coordinating extraction for prompt: {prompt}")
        
        # 1. Initial Extraction from Prompt
        basic_result = await self.process_prompt(prompt)
        
        # 2. Determine Default Proposal Type
        default_proposal_type = "Discussion" if "discussion" in prompt.lower() else "ReferendumV2"
        self.log_info(f"Default proposal type set to: {default_proposal_type}")

        # 3. Consolidate All Proposals to Fetch
        proposals_to_fetch = {}  # Use a dict to store {id: type} to handle duplicates
        
        # Add IDs extracted directly from text with the default type
        for p_id in basic_result.ids:
            if p_id not in proposals_to_fetch:
                proposals_to_fetch[p_id] = default_proposal_type

        # Add IDs and types parsed from links
        parsed_from_links = self._parse_links(basic_result.links)
        for p_id, p_type in parsed_from_links:
            proposals_to_fetch[p_id] = p_type # This will overwrite the default if a link is more specific

        self.log_info(f"Proposals consolidated for fetching: {proposals_to_fetch}")

        # 4. Fetch All Proposal Data in a Single Batch
        proposals = []
        proposal_data_list = []
        
        if proposals_to_fetch:
            # Group by type for efficient fetching
            by_type = {}
            for p_id, p_type in proposals_to_fetch.items():
                if p_type not in by_type:
                    by_type[p_type] = []
                by_type[p_type].append(p_id)

            async with PolkadotAPIClient() as api_client:
                fetch_tasks = []
                for p_type, p_ids in by_type.items():
                    self.log_info(f"Fetching {len(p_ids)} proposals of type {p_type}")
                    fetch_tasks.append(api_client.fetch_multiple_proposals(p_ids, p_type))
                
                results_by_type = await asyncio.gather(*fetch_tasks)
                for result_set in results_by_type:
                    proposal_data_list.extend(result_set)

            # 4.5 Calculate rewards and update proposal data
            for p_data in proposal_data_list:
                p_data.calculated_reward = self._calculate_reward(p_data)
                
            # Convert to ProposalInfo objects
            for proposal_data in proposal_data_list:
                proposals.append(ProposalInfo(**proposal_data.__dict__))
        
        # 5. Generate AI Analysis
        analysis = None
        if proposal_data_list:
            self.log_info("Generating AI analysis of proposals")
            # print(f"\n\n proposal_data_list {proposal_data_list} \n\n")
            analysis = await self.analyzer.analyze_proposals(proposal_data_list)
            self.log_info("AI analysis completed")
        
        # 6. Construct Final Response
        # Ensure final IDs list is unique and matches what was fetched
        final_ids = sorted(list(proposals_to_fetch.keys()), key=int)
        
        return EnhancedExtractionResponse(
            ids=final_ids,
            links=basic_result.links,
            proposals=proposals,
            analysis=analysis
        )
    
    async def process_prompt_with_accountability_check(self, prompt: str) -> AccountabilityCheckResponse:
        """
        Processes a prompt to extract IDs and links, intelligently determines proposal types,
        fetches data, calculates rewards, and generates an AI accountability analysis.
        """
        self.log_info(f"Accountability check coordinating extraction for prompt: {prompt}")
        
        # 1. Initial Extraction from Prompt
        basic_result = await self.process_prompt(prompt)
        
        # 2. Determine Default Proposal Type
        default_proposal_type = "Discussion" if "discussion" in prompt.lower() else "ReferendumV2"
        self.log_info(f"Default proposal type set to: {default_proposal_type}")

        # 3. Consolidate All Proposals to Fetch
        proposals_to_fetch = {}  # Use a dict to store {id: type} to handle duplicates
        
        # Add IDs extracted directly from text with the default type
        for p_id in basic_result.ids:
            if p_id not in proposals_to_fetch:
                proposals_to_fetch[p_id] = default_proposal_type

        # Add IDs and types parsed from links
        parsed_from_links = self._parse_links(basic_result.links)
        for p_id, p_type in parsed_from_links:
            proposals_to_fetch[p_id] = p_type # This will overwrite the default if a link is more specific

        self.log_info(f"Proposals consolidated for accountability check: {proposals_to_fetch}")

        # 4. Fetch All Proposal Data in a Single Batch
        proposals = []
        proposal_data_list = []
        
        if proposals_to_fetch:
            # Group by type for efficient fetching
            by_type = {}
            for p_id, p_type in proposals_to_fetch.items():
                if p_type not in by_type:
                    by_type[p_type] = []
                by_type[p_type].append(p_id)

            async with PolkadotAPIClient() as api_client:
                fetch_tasks = []
                for p_type, p_ids in by_type.items():
                    self.log_info(f"Fetching {len(p_ids)} proposals of type {p_type} for accountability check")
                    fetch_tasks.append(api_client.fetch_multiple_proposals(p_ids, p_type))
                
                results_by_type = await asyncio.gather(*fetch_tasks)
                for result_set in results_by_type:
                    proposal_data_list.extend(result_set)

            # 4.5 Calculate rewards and update proposal data
            for p_data in proposal_data_list:
                p_data.calculated_reward = self._calculate_reward(p_data)
                
            # Convert to ProposalInfo objects
            for proposal_data in proposal_data_list:
                proposals.append(ProposalInfo(**proposal_data.__dict__))
        
        # 5. Generate AI Accountability Analysis
        accountability_analysis = None
        if proposal_data_list:
            self.log_info("Generating AI accountability analysis of proposals")
            accountability_analysis = await self.accountability_analyzer.analyze_proposals_accountability(proposal_data_list)
            self.log_info("AI accountability analysis completed")
        
        # 6. Construct Final Response
        # Ensure final IDs list is unique and matches what was fetched
        final_ids = sorted(list(proposals_to_fetch.keys()), key=int)
        
        return AccountabilityCheckResponse(
            ids=final_ids,
            links=basic_result.links,
            proposals=proposals,
            accountability_analysis=accountability_analysis
        )
    
    # ... process_prompt method remains the same ...
    async def process_prompt(self, prompt: str) -> ExtractionResponse:
        """
        Coordinates the extraction of IDs and links from a given prompt.
        It runs the LLM and Regex agents concurrently and aggregates their results.
        """
        self.log_info(f"Coordinating extraction for prompt: {prompt}")
        
        # Run agents concurrently
        llm_task = asyncio.create_task(self.llm_agent.process(prompt))
        regex_task = asyncio.create_task(self.regex_agent.process(prompt))
        
        llm_result, regex_result = await asyncio.gather(llm_task, regex_task)
        
        # Aggregate and deduplicate results
        combined_ids = sorted(list(set(llm_result.get("ids", []) + regex_result.get("ids", []))), key=int)
        combined_links = sorted(list(set(llm_result.get("links", []) + regex_result.get("links", []))))
        
        self.log_info(f"Coordination completed: {len(combined_ids)} IDs, {len(combined_links)} links")
        
        return ExtractionResponse(ids=combined_ids, links=combined_links)
    
    async def process(self, input_data: str) -> Dict[str, Any]:
        """Generic process method for the agent."""
        return await self.process_prompt_with_proposals(input_data) 