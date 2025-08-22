import asyncio
import re
import os
from typing import Dict, Any, List, Tuple, Optional
from app.agents.base_agent import BaseAgent
from app.agents.llm_extractor_agent import LLMExtractorAgent
from app.agents.regex_extractor_agent import RegexExtractorAgent
from app.models.response_models import ExtractionResponse, EnhancedExtractionResponse, ProposalInfo, AccountabilityCheckResponse, GeneralChatResponse
from app.services.polkadot_api_client import PolkadotAPIClient, ProposalData
from app.services.gemini_analyzer import GeminiAnalyzer
from app.services.accountability_analyzer import AccountabilityAnalyzer
from app.services.general_chat_analyzer import GeneralChatAnalyzer
from app.services.routing_service import RoutingService
from app.services.algolia import search_posts

class CoordinatorAgent(BaseAgent):
    def __init__(self):
        super().__init__("Coordinator")
        self.llm_extractor = LLMExtractorAgent()
        self.regex_extractor = RegexExtractorAgent()
        self.api_client = PolkadotAPIClient()
        self.analyzer = GeminiAnalyzer()
        self.accountability_analyzer = AccountabilityAnalyzer()
        self.general_chat_analyzer = GeneralChatAnalyzer()
        self.routing_service = RoutingService()  # Create instance

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

    async def _process_dynamic_route(self, routing_info: Dict[str, Any]) -> Tuple[List[str], List[str], List[ProposalData]]:
        """
        Process dynamic route using Polkassembly API with extracted IDs.
        
        Args:
            routing_info: Routing information with IDs and proposal type
            
        Returns:
            Tuple of (ids, links, proposal_data_list)
        """
        ids = routing_info.get("ID", [])
        proposal_type = routing_info.get("proposal_type", "ReferendumV2")
        
        self.log_info(f"Processing DYNAMIC route: {len(ids)} IDs of type {proposal_type}")
        
        # 3. Fetch proposals from Polkassembly API
        if ids:
            self.log_info(f"Fetching {len(ids)} proposal(s) of type {proposal_type}")
            proposal_data_list = await self.api_client.fetch_multiple_proposals(ids, proposal_type)
                
            # Calculate rewards
            for p_data in proposal_data_list:
                p_data.calculated_reward = self._calculate_reward(p_data)
        
        return ids, [], proposal_data_list
    
    async def _process_algolia_result_with_gemini(self, prompt: str, proposal_data_list: List[ProposalData]) -> str:
        """
        Process Algolia results with Gemini to generate intelligent analysis
        
        Args:
            prompt: The original user query
            proposal_data_list: List of proposal data retrieved from Polkassembly API
            
        Returns:
            Gemini's analysis response
        """
        if not proposal_data_list:
            return "No proposals were retrieved from the search API."
        
        # Create a comprehensive prompt for Gemini
        gemini_prompt = f"""This is the prompt: "{prompt}"

Below are the proposals retrieved from the search API. Now according to the question, find the best answer from the proposals below:

"""
        
        # Add each proposal's details to the prompt
        for i, proposal in enumerate(proposal_data_list, 1):
            gemini_prompt += f"""
PROPOSAL {i}:
- ID: {proposal.id}
- Type: {proposal.proposal_type}
- Title: {proposal.title}
- Status: {proposal.status}
- Proposer: {proposal.proposer}
- Created: {proposal.created_at}
- Reward: {proposal.calculated_reward}
- Content: {proposal.content}
"""
            
            if proposal.vote_metrics:
                gemini_prompt += f"- Vote Metrics: {proposal.vote_metrics}\n"
            if proposal.timeline:
                gemini_prompt += f"- Timeline: {proposal.timeline}\n"
            if proposal.beneficiaries:
                gemini_prompt += f"- Beneficiaries: {proposal.beneficiaries}\n"
            
            gemini_prompt += "\n---\n"
        
        gemini_prompt += f"""
Please provide a comprehensive answer to the user's query: "{prompt}"

Focus on:
1. Directly answering their specific question
2. Using relevant information from the proposals above
3. Providing context and insights that would be helpful
4. If multiple proposals are relevant, compare and contrast them as needed

Use markdown formatting for better readability and structure your response logically.
"""
        
        # Send to Gemini for analysis
        try:
            self.log_info(f"Sending {len(proposal_data_list)} proposals to Gemini for analysis")
            
            if len(proposal_data_list) == 1:
                analysis = await self.analyzer.analyze_single_proposal(proposal_data_list[0], custom_prompt=gemini_prompt)
            else:
                analysis = await self.analyzer.compare_proposals(proposal_data_list, custom_prompt=gemini_prompt)
            
            if not analysis or "Could not generate" in analysis:
                analysis = f"Found {len(proposal_data_list)} relevant proposal(s) for your query '{prompt}', but AI analysis is currently unavailable."
            
            self.log_info("Gemini analysis completed for Algolia results")
            return analysis
            
        except Exception as e:
            self.log_error(f"Error in Gemini analysis for Algolia results: {str(e)}")
            return f"Found {len(proposal_data_list)} relevant proposal(s) for your query '{prompt}', but AI analysis encountered an error: {str(e)}"

    async def _process_algolia_result_with_accountability_check(self, prompt: str, proposal_data_list: List[ProposalData]) -> str:
        """
        Process Algolia results with accountability analysis using Gemini
        
        Args:
            prompt: The original user query
            proposal_data_list: List of proposal data retrieved from Polkassembly API
            
        Returns:
            Gemini's accountability analysis response
        """
        if not proposal_data_list:
            return "No proposals were retrieved from the search API for accountability analysis."
        
        # Create a comprehensive accountability prompt for Gemini
        gemini_prompt = f"""This is the prompt: "{prompt}"

Below are the proposals retrieved from the search API. Now according to the question, perform an accountability analysis on the proposals below based on governance best practices:

"""
        
        # Add each proposal's details to the prompt
        for i, proposal in enumerate(proposal_data_list, 1):
            gemini_prompt += f"""
PROPOSAL {i}:
- ID: {proposal.id}
- Type: {proposal.proposal_type}
- Title: {proposal.title}
- Status: {proposal.status}
- Proposer: {proposal.proposer}
- Created: {proposal.created_at}
- Reward: {proposal.calculated_reward}
- Content: {proposal.content}
"""
            
            if proposal.vote_metrics:
                gemini_prompt += f"- Vote Metrics: {proposal.vote_metrics}\n"
            if proposal.timeline:
                gemini_prompt += f"- Timeline: {proposal.timeline}\n"
            if proposal.beneficiaries:
                gemini_prompt += f"- Beneficiaries: {proposal.beneficiaries}\n"
            
            gemini_prompt += "\n---\n"
        
        # Define accountability checkpoints
        accountability_checkpoints = [
            "Economic feasibility and cost sharing",
            "Technical implementation and specifications", 
            "Governance approvals and inter-ecosystem agreements",
            "Storage token decision and neutrality",
            "Strategic benefit delivery",
            "Validator set and security model",
            "Public communication and stakeholder engagement"
        ]
        
        checkpoints_text = "\n".join([f"- {checkpoint}" for checkpoint in accountability_checkpoints])
        
        gemini_prompt += f"""
Please perform a comprehensive accountability analysis for the user's query: "{prompt}"

**Instructions:**
Analyze the proposals against the following accountability checkpoints. For each checkpoint, provide:
1. A status indicator: ✅ (Strong), ⚠️ (Moderate), ❌ (Weak/Missing)
2. A brief 1-2 sentence assessment explaining your rating

**Accountability Checkpoints:**
{checkpoints_text}

Focus on:
1. Directly answering their specific accountability question
2. Using relevant information from the proposals above
3. Providing governance accountability insights
4. If multiple proposals are relevant, compare their accountability measures

Use markdown formatting for better readability and structure your response logically.
"""
        
        # Send to Gemini for accountability analysis
        try:
            self.log_info(f"Sending {len(proposal_data_list)} proposals to Gemini for accountability analysis")
            
            # Use the accountability analyzer with custom prompt
            if len(proposal_data_list) == 1:
                analysis = await self.analyzer.analyze_single_proposal(proposal_data_list[0], custom_prompt=gemini_prompt)
            else:
                analysis = await self.analyzer.compare_proposals(proposal_data_list, custom_prompt=gemini_prompt)
            
            if not analysis or "Could not generate" in analysis:
                analysis = f"Found {len(proposal_data_list)} relevant proposal(s) for accountability analysis of your query '{prompt}', but AI analysis is currently unavailable."
            
            self.log_info("Gemini accountability analysis completed for Algolia results")
            return analysis
            
        except Exception as e:
            self.log_error(f"Error in Gemini accountability analysis for Algolia results: {str(e)}")
            return f"Found {len(proposal_data_list)} relevant proposal(s) for accountability analysis of your query '{prompt}', but AI analysis encountered an error: {str(e)}"


    async def _process_algolia_route(self, routing_info: dict) -> Tuple[List[str], List[str], List[ProposalData]]:
        """
        Process Algolia route by extracting keywords and searching
        
        Args:
            routing_info: Routing information containing keywords and search data
            
        Returns:
            Tuple of (ids, links, proposal_data_list)
        """
        # Import here to avoid circular imports
        from app.services.algolia import search_posts
        
        # Extract keywords from routing info
        keywords = routing_info.get("keywords", "")
        num_results = os.getenv("ALGOLIA_NUM_RESULTS", 5)  # Default number of results
        
        self.log_info(f"Processing ALGOLIA route: Searching for keywords '{keywords}'")
        
        # Get search results from Algolia
        search_results = await search_posts(keywords, num_results)
        
        post_indexes = {}
        for i, post in enumerate(search_results, 1):
            post_indexes[post.get('index', 'Unknown')] = post.get('proposalType', 'Unknown')

        print(f"post_indexes is {post_indexes}")
        
        # Now fetch detailed data from Polkassembly API
        proposal_data_list = []
        ids = []
        
        # Group proposals by type for efficient fetching
        by_type = {}
        for proposal_id, proposal_type in post_indexes.items():
            if proposal_id != 'Unknown':  # Skip invalid IDs
                proposal_id_str = str(proposal_id)
                ids.append(proposal_id_str)
                
                if proposal_type not in by_type:
                    by_type[proposal_type] = []
                by_type[proposal_type].append(proposal_id_str)
        
        print(f"Grouped by type: {by_type}")
        
        # Fetch proposals by type
        if by_type:
            fetch_tasks = []
            for p_type, p_ids in by_type.items():
                print(f"Fetching {len(p_ids)} proposals of type {p_type}: {p_ids}")
                fetch_tasks.append(self.api_client.fetch_multiple_proposals(p_ids, p_type))
            
            # Execute all fetch tasks concurrently
            results_by_type = await asyncio.gather(*fetch_tasks)
            
            # Combine all results
            for result_set in results_by_type:
                proposal_data_list.extend(result_set)
            
            # Calculate rewards for each proposal
            for p_data in proposal_data_list:
                p_data.calculated_reward = self._calculate_reward(p_data)
            
            # Print detailed information about fetched proposals
            print(f"\n=== FETCHED {len(proposal_data_list)} DETAILED PROPOSALS ===")
            for i, proposal in enumerate(proposal_data_list, 1):
                print(f"\nProposal {i}:")
                print(f"  ID: {proposal.id}")
                print(f"  Type: {proposal.proposal_type}")
                print(f"  Title: {proposal.title}")
                print(f"  Status: {proposal.status}")
                print(f"  Proposer: {proposal.proposer}")
                print(f"  Created: {proposal.created_at}")
                print(f"  Calculated Reward: {proposal.calculated_reward}")
                print(f"  Content Length: {len(proposal.content)} characters")
                print(f"  Content Preview: {proposal.content}...")
                if proposal.beneficiaries:
                    print(f"  Beneficiaries: {len(proposal.beneficiaries)} entries")
                if proposal.vote_metrics:
                    print(f"  Vote Metrics: {proposal.vote_metrics}")
                if proposal.timeline:
                    print(f"  Timeline: {len(proposal.timeline)} events")
                if hasattr(proposal, 'error') and proposal.error:
                    print(f"  ERROR: {proposal.error}")
                print(f"  ---")
        
        return proposal_data_list 

    async def process_prompt_with_proposals(self, prompt: str) -> EnhancedExtractionResponse:
        """
        Processes a prompt using intelligent routing to determine data source,
        fetches data accordingly, and generates an AI analysis.
        """
        self.log_info(f"Enhanced coordinating extraction for prompt: {prompt}")
        
        # 1. Route the request using Gemini-powered routing service
        routing_info = await self.routing_service.process_routed_request(prompt)
        print(f"\n\n\n routing_info is {routing_info} \n\n\n")
        data_source = routing_info.get("data_source", "dynamic")
        
        self.log_info(f"Request routed to: {data_source.upper()}")
        
        # 2. Process based on routing decision
        if data_source == "dynamic":
            ids, links, proposal_data_list = await self._process_dynamic_route(routing_info)
        elif data_source == "algolia":
            proposal_data_list = await self._process_algolia_route(routing_info)
            
            # Extract IDs from proposal data for response
            ids = [p.id for p in proposal_data_list]
            links = []  # Algolia doesn't provide direct links
            
            # Get Gemini analysis of the Algolia results
            analysis = await self._process_algolia_result_with_gemini(prompt, proposal_data_list)
        else:
            # Fallback to original logic
            self.log_warning(f"Unknown data source '{data_source}', falling back to original logic")
            basic_result = await self.process_prompt(prompt)
            default_proposal_type = "Discussion" if "discussion" in prompt.lower() else "ReferendumV2"
            
            proposals_to_fetch = {}
            for p_id in basic_result.ids:
                proposals_to_fetch[p_id] = default_proposal_type
            
            parsed_from_links = self._parse_links(basic_result.links)
            for p_id, p_type in parsed_from_links:
                proposals_to_fetch[p_id] = p_type
            
            ids = sorted(list(proposals_to_fetch.keys()), key=int)
            links = basic_result.links
            proposal_data_list = []
            
            if proposals_to_fetch:
                async with PolkadotAPIClient() as api_client:
                    by_type = {}
                    for p_id, p_type in proposals_to_fetch.items():
                        if p_type not in by_type:
                            by_type[p_type] = []
                        by_type[p_type].append(p_id)
                    
                    fetch_tasks = []
                    for p_type, p_ids in by_type.items():
                        fetch_tasks.append(self.api_client.fetch_multiple_proposals(p_ids, p_type))
                    
                    results_by_type = await asyncio.gather(*fetch_tasks)
                    for result_set in results_by_type:
                        proposal_data_list.extend(result_set)
                
                for p_data in proposal_data_list:
                    p_data.calculated_reward = self._calculate_reward(p_data)

        # 3. Check if we have any valid data before proceeding
        valid_proposals = [p for p in proposal_data_list if not (hasattr(p, 'error') and p.error)]
        
        if not valid_proposals:
            self.log_info("No valid proposal data retrieved - returning empty response without AI analysis")
            return EnhancedExtractionResponse(
                ids=ids,
                links=links,
                proposals=[],
                analysis=""
            )

        # 4. Convert to ProposalInfo objects
        proposals = []
        for proposal_data in valid_proposals:
            proposals.append(ProposalInfo(**proposal_data.__dict__))
        
        # 5. Generate AI Analysis only if we have valid data and it's not already generated (Algolia case)
        if data_source == "algolia":
            # Analysis already generated in _process_algolia_result_with_gemini
            pass
        else:
            # Generate analysis for dynamic and fallback cases
            analysis = None
            if valid_proposals:
                self.log_info(f"Generating AI analysis for {len(valid_proposals)} valid proposals")
                analysis = await self.analyzer.analyze_proposals(valid_proposals)
                self.log_info("AI analysis completed")
        
        # 6. Construct Final Response
        return EnhancedExtractionResponse(
            ids=ids,
            links=links,
            proposals=proposals,
            analysis=analysis
        )

    async def process_prompt_with_accountability_check(self, prompt: str) -> AccountabilityCheckResponse:
        """
        Processes a prompt using intelligent routing for accountability analysis.
        """
        self.log_info(f"Accountability check coordinating extraction for prompt: {prompt}")
        
        # 1. Route the request using Gemini-powered routing service
        routing_info = await self.routing_service.process_routed_request(prompt)
        data_source = routing_info.get("data_source", "dynamic")
        
        self.log_info(f"Accountability request routed to: {data_source.upper()}")
        
        # 2. Process based on routing decision
        if data_source == "dynamic":
            ids, links, proposal_data_list = await self._process_dynamic_route(routing_info)
        elif data_source == "algolia":
            proposal_data_list = await self._process_algolia_route(routing_info)
            
            # Extract IDs from proposal data for response
            ids = [p.id for p in proposal_data_list]
            links = []  # Algolia doesn't provide direct links
            
            # Get Gemini accountability analysis of the Algolia results
            accountability_analysis = await self._process_algolia_result_with_accountability_check(prompt, proposal_data_list)
        else:
            # Fallback to original logic (same as above)
            self.log_warning(f"Unknown data source '{data_source}', falling back to original logic")
            basic_result = await self.process_prompt(prompt)
            default_proposal_type = "Discussion" if "discussion" in prompt.lower() else "ReferendumV2"
            
            proposals_to_fetch = {}
            for p_id in basic_result.ids:
                proposals_to_fetch[p_id] = default_proposal_type
            
            parsed_from_links = self._parse_links(basic_result.links)
            for p_id, p_type in parsed_from_links:
                proposals_to_fetch[p_id] = p_type
            
            ids = sorted(list(proposals_to_fetch.keys()), key=int)
            links = basic_result.links
            proposal_data_list = []
            
            if proposals_to_fetch:
                async with PolkadotAPIClient() as api_client:
                    by_type = {}
                    for p_id, p_type in proposals_to_fetch.items():
                        if p_type not in by_type:
                            by_type[p_type] = []
                        by_type[p_type].append(p_id)
                    
                    fetch_tasks = []
                    for p_type, p_ids in by_type.items():
                        fetch_tasks.append(self.api_client.fetch_multiple_proposals(p_ids, p_type))
                    
                    results_by_type = await asyncio.gather(*fetch_tasks)
                    for result_set in results_by_type:
                        proposal_data_list.extend(result_set)
                
                for p_data in proposal_data_list:
                    p_data.calculated_reward = self._calculate_reward(p_data)

        # 3. Check if we have any valid data before proceeding
        valid_proposals = [p for p in proposal_data_list if not (hasattr(p, 'error') and p.error)]
        
        if not valid_proposals:
            self.log_info("No valid proposal data retrieved - returning empty response without accountability analysis")
            return AccountabilityCheckResponse(
                ids=ids,
                links=links,
                proposals=[],
                accountability_analysis=""
            )

        # 4. Convert to ProposalInfo objects
        proposals = []
        for proposal_data in valid_proposals:
            proposals.append(ProposalInfo(**proposal_data.__dict__))
        
        # 5. Generate AI Accountability Analysis only if we have valid data and it's not already generated (Algolia case)
        if data_source == "algolia":
            # Accountability analysis already generated in _process_algolia_result_with_accountability_check
            pass
        else:
            # Generate accountability analysis for dynamic and fallback cases
            accountability_analysis = None
            if valid_proposals:
                self.log_info(f"Generating AI accountability analysis for {len(valid_proposals)} valid proposals")
                accountability_analysis = await self.accountability_analyzer.analyze_proposals_accountability(valid_proposals)
                self.log_info("AI accountability analysis completed")
        
        # 6. Construct Final Response
        return AccountabilityCheckResponse(
            ids=ids,
            links=links,
            proposals=proposals,
            accountability_analysis=accountability_analysis
        )
    
    # ... process_prompt method remains the same ...
    async def process_prompt_with_general_chat(self, prompt: str) -> GeneralChatResponse:
        """
        Processes a prompt using intelligent routing for general question answering.
        Uses the same logic as accountability check but with direct Q&A prompts.
        """
        self.log_info(f"General chat coordinating extraction for prompt: {prompt}")
        
        # 1. Route the request using Gemini-powered routing service
        routing_info = await self.routing_service.process_routed_request(prompt)
        data_source = routing_info.get("data_source", "dynamic")
        
        self.log_info(f"General chat request routed to: {data_source.upper()}")
        
        # 2. Process based on routing decision
        if data_source == "dynamic":
            ids, links, proposal_data_list = await self._process_dynamic_route(routing_info)
        elif data_source == "algolia":
            proposal_data_list = await self._process_algolia_route(routing_info)
            
            # Extract IDs from proposal data for response
            ids = [p.id for p in proposal_data_list]
            links = []  # Algolia doesn't provide direct links
        else:
            # Fallback case
            self.log_info("Using fallback extraction for general chat")
            extraction_result = await self.process_prompt(prompt)
            ids = extraction_result.ids
            links = extraction_result.links
            
            if ids:
                # Fetch proposal data
                proposals_to_fetch = {}
                for proposal_id in ids:
                    proposals_to_fetch[proposal_id] = "ReferendumV2"  # Default type
                
                if links:
                    parsed_links = self._parse_links(links)
                    for link_id, link_type in parsed_links:
                        proposals_to_fetch[link_id] = link_type
                
                proposal_data_list = []
                if proposals_to_fetch:
                    async with PolkadotAPIClient() as api_client:
                        by_type = {}
                        for p_id, p_type in proposals_to_fetch.items():
                            if p_type not in by_type:
                                by_type[p_type] = []
                            by_type[p_type].append(p_id)
                        
                        fetch_tasks = []
                        for p_type, p_ids in by_type.items():
                            fetch_tasks.append(self.api_client.fetch_multiple_proposals(p_ids, p_type))
                        
                        results_by_type = await asyncio.gather(*fetch_tasks)
                        for result_set in results_by_type:
                            proposal_data_list.extend(result_set)
                    
                    for p_data in proposal_data_list:
                        p_data.calculated_reward = self._calculate_reward(p_data)
            else:
                proposal_data_list = []

        # 3. Check if we have any valid data before proceeding
        valid_proposals = [p for p in proposal_data_list if not (hasattr(p, 'error') and p.error)]
        
        if not valid_proposals:
            self.log_info("No valid proposal data retrieved - returning empty response without answer")
            return GeneralChatResponse(
                ids=ids,
                links=links,
                proposals=[],
                answer=""
            )

        # 4. Convert to ProposalInfo objects
        proposals = []
        for proposal_data in valid_proposals:
            proposals.append(ProposalInfo(**proposal_data.__dict__))
        
        # 5. Generate AI Answer only if we have valid data
        answer = None
        if valid_proposals:
            self.log_info(f"Generating AI answer for {len(valid_proposals)} valid proposals")
            answer = await self.general_chat_analyzer.analyze_proposals_general_chat(valid_proposals, prompt)
            self.log_info("AI answer generation completed")
        
        # 6. Construct Final Response
        return GeneralChatResponse(
            ids=ids,
            links=links,
            proposals=proposals,
            answer=answer if answer else ""
        )

    async def process_prompt(self, prompt: str) -> ExtractionResponse:
        """
        Coordinates the extraction of IDs and links from a given prompt.
        It runs the LLM and Regex agents concurrently and aggregates their results.
        """
        self.log_info(f"Coordinating extraction for prompt: {prompt}")
        
        # Run agents concurrently
        llm_task = asyncio.create_task(self.llm_extractor.process(prompt))
        regex_task = asyncio.create_task(self.regex_extractor.process(prompt))
        
        llm_result, regex_result = await asyncio.gather(llm_task, regex_task)
        
        # Aggregate and deduplicate results
        combined_ids = sorted(list(set(llm_result.get("ids", []) + regex_result.get("ids", []))), key=int)
        combined_links = sorted(list(set(llm_result.get("links", []) + regex_result.get("links", []))))
        
        self.log_info(f"Coordination completed: {len(combined_ids)} IDs, {len(combined_links)} links")
        
        return ExtractionResponse(ids=combined_ids, links=combined_links)
    
    async def process(self, input_data: str) -> Dict[str, Any]:
        """Generic process method for the agent."""
        return await self.process_prompt_with_proposals(input_data) 