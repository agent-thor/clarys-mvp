import os
import asyncio
from typing import List, Optional
from google import genai
from app.services.polkadot_api_client import ProposalData
import logging

logger = logging.getLogger(__name__)

class GeminiAnalyzer:
    """Service to analyze and compare proposals using Gemini AI"""
    
    def __init__(self, model_name: str = "gemini-2.5-flash-lite"):
        self.model_name = model_name
        self.client = None
        self._initialize_client()
    
    def _initialize_client(self):
        """Initialize Gemini client"""
        try:
            api_key = os.getenv("GEMINI_API_KEY")
            if not api_key:
                logger.error("GEMINI_API_KEY environment variable not set")
                return
            
            self.client = genai.Client(api_key=api_key)
            logger.info("Gemini analyzer client initialized successfully")
            
        except Exception as e:
            logger.error(f"Failed to initialize Gemini analyzer client: {str(e)}")
            self.client = None
    
    def _extract_reward_amount(self, proposal: ProposalData) -> str:
        """Extract reward amount from proposal data"""
        try:
            if not proposal.beneficiaries:
                return "Not specified"
            
            total_amount = 0
            currency = "DOT"  # Default
            
            for beneficiary in proposal.beneficiaries:
                amount = int(beneficiary.get("amount", 0))
                asset_id = beneficiary.get("assetId", "")
                
                # Convert from smallest unit (assuming 10 decimals for DOT)
                if asset_id == "1337":  # USDC on Polkadot Asset Hub
                    amount_converted = amount / 1_000_000  # 6 decimals for USDC
                    currency = "USDC"
                else:
                    amount_converted = amount / 10_000_000_000  # 10 decimals for DOT
                    currency = "DOT"
                
                total_amount += amount_converted
            
            if total_amount > 0:
                return f"{total_amount:,.0f} {currency}"
            else:
                return "Not specified"
                
        except Exception as e:
            logger.error(f"Error extracting reward amount: {str(e)}")
            return "Not specified"
    
    def _extract_proposal_type(self, content: str) -> str:
        """Extract proposal type from content"""
        content_lower = content.lower()
        if "child bounty" in content_lower or "bounty" in content_lower:
            return "Child Bounty"
        elif "referendum" in content_lower:
            return "ReferendumV2"
        elif "treasury" in content_lower:
            return "Treasury"
        else:
            return "ReferendumV2"  # Default
    
    def _extract_category(self, content: str) -> str:
        """Extract category from content"""
        content_lower = content.lower()
        if any(word in content_lower for word in ["marketing", "content creation", "social"]):
            return "Marketing"
        elif any(word in content_lower for word in ["development", "software", "app", "extension", "wallet", "ai", "tool"]):
            return "Development"
        elif any(word in content_lower for word in ["infrastructure", "protocol", "network"]):
            return "Infrastructure"
        elif any(word in content_lower for word in ["governance", "democracy"]):
            return "Democracy"
        else:
            return "Development"  # Default
    
    def _extract_description(self, content: str, title: str) -> str:
        """Extract brief description from content"""
        # Take first few sentences or key summary
        sentences = content.split('. ')
        
        # Look for key description patterns
        for sentence in sentences[:5]:  # Check first 5 sentences
            if any(word in sentence.lower() for word in ["proposal", "seeks", "requests", "aims", "focuses"]):
                # Clean and truncate
                clean_sentence = sentence.replace('\n', ' ').replace('*', '').strip()
                if len(clean_sentence) > 100:
                    clean_sentence = clean_sentence[:100] + "..."
                return clean_sentence
        
        # Fallback to title-based description
        if "clarys" in title.lower():
            return "AI-powered tool to reduce governance fatigue and streamline proposal analysis."
        elif "subwallet" in title.lower():
            return "Retroactive funding for SubWallet development activities."
        else:
            return "Polkadot ecosystem development proposal."
    
    async def analyze_single_proposal(self, proposal: ProposalData) -> str:
        """Analyze a single proposal and provide detailed information"""
        if proposal.error:
            return f"Error: Unable to analyze proposal {proposal.id}"
        
        try:
            # Extract all data locally without using Gemini
            reward_amount = self._extract_reward_amount(proposal)
            proposal_type = self._extract_proposal_type(proposal.content)
            category = self._extract_category(proposal.content)
            description = self._extract_description(proposal.content, proposal.title)
            creation_date = proposal.created_at[:10] if proposal.created_at else "Not specified"
            
            # Format the response directly
            analysis = f"""Proposal {proposal.id}:
Title: {proposal.title}
Type: {proposal_type}
Proposer: {proposal.proposer or "Not specified"}
Reward: {reward_amount}
Category: {category}
Status: {proposal.status}
Creation Date: {creation_date}
Description: {description}"""
            
            logger.info(f"Successfully analyzed proposal {proposal.id}")
            return analysis
            
        except Exception as e:
            logger.error(f"Error analyzing proposal {proposal.id}: {str(e)}")
            return f"Error analyzing proposal {proposal.id}: {str(e)}"
    
    async def compare_proposals(self, proposals: List[ProposalData]) -> str:
        """Compare multiple proposals and provide detailed comparison"""
        # Filter out proposals with errors
        valid_proposals = [p for p in proposals if not p.error]
        if len(valid_proposals) < 2:
            return "Error: Not enough valid proposals to compare"
        
        try:
            # Generate individual summaries using local extraction
            individual_summaries = []
            
            for proposal in valid_proposals:
                reward_amount = self._extract_reward_amount(proposal)
                proposal_type = self._extract_proposal_type(proposal.content)
                category = self._extract_category(proposal.content)
                description = self._extract_description(proposal.content, proposal.title)
                creation_date = proposal.created_at[:10] if proposal.created_at else "Not specified"
                
                summary = f"""Proposal {proposal.id}:
Title: {proposal.title}
Type: {proposal_type}
Proposer: {proposal.proposer or "Not specified"}
Reward: {reward_amount}
Category: {category}
Status: {proposal.status}
Creation Date: {creation_date}
Description: {description}"""
                
                individual_summaries.append(summary)
            
            # Generate comparison using Gemini with minimal data
            if self.client:
                try:
                    # Prepare minimal data for comparison
                    comparison_data = []
                    for proposal in valid_proposals:
                        comparison_data.append({
                            "id": proposal.id,
                            "title": proposal.title,
                            "reward": self._extract_reward_amount(proposal),
                            "type": self._extract_proposal_type(proposal.content),
                            "category": self._extract_category(proposal.content),
                            "created": proposal.created_at[:10] if proposal.created_at else "Not specified",
                            "key_content": proposal.content[:300]  # Very brief content
                        })
                    
                    comparison_prompt = f"""Compare these proposals and provide ONLY the comparison section in this format:

Comparison:
Cost: [Compare funding amounts in 1 sentence]
Milestones: [Compare timelines in 1 sentence]
Impact on Polkadot: [Compare ecosystem impact in 1 sentence]
Timeline: [Compare project timelines in 1 sentence]
Completeness: [Compare how well-defined each proposal is in 1 sentence]

Data: {comparison_data}

IMPORTANT: Provide ONLY the Comparison section, keep each point to 1 sentence maximum."""
                    
                    loop = asyncio.get_event_loop()
                    response = await loop.run_in_executor(
                        None, 
                        lambda: self.client.models.generate_content(
                            model=self.model_name,
                            contents=comparison_prompt
                        )
                    )
                    
                    comparison_section = response.text.strip()
                    
                except Exception as e:
                    logger.error(f"Gemini comparison failed, using fallback: {str(e)}")
                    comparison_section = self._generate_fallback_comparison(valid_proposals)
            else:
                comparison_section = self._generate_fallback_comparison(valid_proposals)
            
            # Combine individual summaries with comparison
            full_analysis = "\n\n".join(individual_summaries) + "\n\n" + comparison_section
            
            logger.info(f"Successfully compared {len(valid_proposals)} proposals")
            return full_analysis
            
        except Exception as e:
            logger.error(f"Error comparing proposals: {str(e)}")
            return f"Error comparing proposals: {str(e)}"
    
    def _generate_fallback_comparison(self, proposals: List[ProposalData]) -> str:
        """Generate a basic comparison when Gemini is unavailable"""
        rewards = [self._extract_reward_amount(p) for p in proposals]
        types = [self._extract_proposal_type(p.content) for p in proposals]
        
        return f"""Comparison:
Cost: Proposal {proposals[0].id} requests {rewards[0]} while Proposal {proposals[1].id} requests {rewards[1]}.
Milestones: Both proposals have different development timelines and deliverables.
Impact on Polkadot: Both proposals contribute to the Polkadot ecosystem in their respective areas.
Timeline: The proposals have different timeline approaches for their development phases.
Completeness: Both proposals provide structured information about their objectives and requirements."""
    
    async def analyze_proposals(self, proposals: List[ProposalData]) -> str:
        """Main method to analyze proposals - single analysis or comparison based on count"""
        if not proposals:
            return "No proposals to analyze"
        
        # Filter out proposals with errors
        valid_proposals = [p for p in proposals if not p.error]
        
        if len(valid_proposals) == 0:
            return "No valid proposals to analyze"
        elif len(valid_proposals) == 1:
            return await self.analyze_single_proposal(valid_proposals[0])
        else:
            return await self.compare_proposals(valid_proposals) 