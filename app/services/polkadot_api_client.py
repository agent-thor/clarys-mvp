import asyncio
import httpx
import logging
from typing import List, Dict, Any, Optional
from dataclasses import dataclass, field

logger = logging.getLogger(__name__)

@dataclass
class ProposalData:
    """Data class to hold proposal information"""
    id: str
    title: str
    content: str
    status: str
    created_at: str
    proposal_type: str = "ReferendumV2"  # Add the missing proposal_type field
    proposer: Optional[str] = None
    beneficiaries: List[Dict] = field(default_factory=list)
    vote_metrics: Optional[Dict] = None
    timeline: List[Dict] = field(default_factory=list)
    error: Optional[str] = None
    # New field to hold the pre-calculated reward
    calculated_reward: Optional[str] = None

class PolkadotAPIClient:
    """Client for fetching proposal data from Polkadot Polkassembly API"""
    
    def __init__(self, base_url: str = "https://polkadot.polkassembly.io/api/v2", timeout: int = 30):
        self.base_url = base_url
        self.timeout = timeout
        self.client = httpx.AsyncClient(timeout=timeout)
        
    async def __aenter__(self):
        return self
        
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.client.aclose()
    
    async def fetch_proposal(self, proposal_id: str, proposal_type: str = "ReferendumV2") -> ProposalData:
        """
        Fetch a single proposal by ID and type
        
        Args:
            proposal_id: The proposal ID (e.g., "1679")
            proposal_type: The proposal type (e.g., "ReferendumV2")
            
        Returns:
            ProposalData object with proposal information
        """
        url = f"{self.base_url}/{proposal_type}/{proposal_id}"
        
        try:
            logger.info(f"Fetching proposal from: {url}")
            
            response = await self.client.get(url)
            response.raise_for_status()
            
            data = response.json()
            
            # Extract relevant information from the API response
            return ProposalData(
                id=proposal_id,
                title=data.get("title", f"Proposal {proposal_id}"),
                content=data.get("content", ""),
                status=data.get("onChainInfo", {}).get("status", "Status not found"),
                created_at=data.get("createdAt", ""),
                proposer=data.get("onChainInfo", {}).get("proposer"),
                beneficiaries=data.get("onChainInfo", {}).get("beneficiaries", []),
                vote_metrics=data.get("onChainInfo", {}).get("voteMetrics"),
                timeline=data.get("onChainInfo", {}).get("timeline", []),
                proposal_type=proposal_type # Store the proposal_type
            )
            
        except httpx.HTTPStatusError as e:
            error_msg = f"HTTP error {e.response.status_code} for proposal {proposal_id}"
            logger.error(error_msg)
            return ProposalData(
                id=proposal_id,
                title="Error",
                content="",
                status="Error",
                created_at="",
                error=error_msg
            )
            
        except Exception as e:
            error_msg = f"Failed to fetch proposal {proposal_id}: {str(e)}"
            logger.error(error_msg)
            return ProposalData(
                id=proposal_id,
                title="Error",
                content="",
                status="Error", 
                created_at="",
                error=error_msg
            )
    
    async def fetch_multiple_proposals(
        self, 
        proposal_ids: List[str], 
        proposal_type: str = "ReferendumV2"
    ) -> List[ProposalData]:
        """
        Fetch multiple proposals concurrently
        
        Args:
            proposal_ids: List of proposal IDs
            proposal_type: The proposal type (default: "ReferendumV2")
            
        Returns:
            List of ProposalData objects
        """
        if not proposal_ids:
            return []
        
        logger.info(f"Fetching {len(proposal_ids)} proposals of type {proposal_type}")
        
        # Create tasks for concurrent fetching
        tasks = [
            self.fetch_proposal(proposal_id, proposal_type) 
            for proposal_id in proposal_ids
        ]
        
        # Execute all tasks concurrently
        proposals = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Handle any exceptions that occurred
        results = []
        for i, result in enumerate(proposals):
            if isinstance(result, Exception):
                error_msg = f"Exception fetching proposal {proposal_ids[i]}: {str(result)}"
                logger.error(error_msg)
                results.append(ProposalData(
                    id=proposal_ids[i],
                    title="Error",
                    content="",
                    status="Error",
                    created_at="",
                    error=error_msg
                ))
            else:
                results.append(result)
        
        successful_fetches = len([r for r in results if not r.error])
        logger.info(f"Successfully fetched {successful_fetches}/{len(proposal_ids)} proposals")
        
        return results
    
    async def close(self):
        """Close the HTTP client"""
        await self.client.aclose()

# Convenience function for easy usage
async def fetch_proposals_for_ids(
    proposal_ids: List[str], 
    proposal_type: str = "ReferendumV2"
) -> List[ProposalData]:
    """
    Convenience function to fetch proposals for a list of IDs
    
    Args:
        proposal_ids: List of proposal IDs to fetch
        proposal_type: Type of proposals (default: "ReferendumV2")
        
    Returns:
        List of ProposalData objects
    """
    async with PolkadotAPIClient() as client:
        return await client.fetch_multiple_proposals(proposal_ids, proposal_type) 