import os
import asyncio
import re
from typing import Dict, Any, List, Optional
from google import genai
import logging

logger = logging.getLogger(__name__)

class RoutingService:
    """
    Service that uses Gemini to intelligently route requests to either:
    1. Dynamic - Polkassembly API for specific proposal IDs
    2. Algolia - Search engine for keyword-based searches
    """
    
    def __init__(self, model_name: str = "gemini-2.5-flash-lite"):
        self.model_name = model_name
        self.client = None
        self._initialize_client()

    def _initialize_client(self):
        """Initializes the Gemini client for routing decisions."""
        api_key = os.getenv("GEMINI_API_KEY")
        if not api_key:
            logger.warning("GEMINI_API_KEY not found. RoutingService will use fallback logic.")
            return
        
        try:
            self.client = genai.Client(api_key=api_key)
            logger.info("Gemini client initialized successfully (routing_service).")
        except Exception as e:
            logger.error(f"Failed to initialize Gemini client: {str(e)}")
            self.client = None

    async def _safe_gemini_call(self, prompt: str) -> str:
        """Safe async Gemini API call."""
        loop = asyncio.get_event_loop()
        response = await loop.run_in_executor(
            None,
            lambda: self.client.models.generate_content(
                model=self.model_name,
                contents=prompt
            )
        )
        return response.text.strip()

    def _fallback_routing_logic(self, prompt: str) -> Dict[str, Any]:
        """
        Fallback routing logic when Gemini is not available.
        Uses regex patterns to detect IDs and route accordingly.
        """
        # Pattern for detecting specific IDs
        id_patterns = [
            r'\b(?:proposal|referenda?|referendum|discussion)\s+(?:id\s+)?(\d+)\b',
            r'\b(\d+)\s*(?:proposal|referenda?|referendum|discussion)\b',
            r'\b(?:id|#)\s*(\d+)\b'
        ]
        
        extracted_ids = []
        for pattern in id_patterns:
            matches = re.findall(pattern, prompt.lower())
            extracted_ids.extend(matches)
        
        # Remove duplicates and convert to integers for sorting
        unique_ids = sorted(list(set(extracted_ids)), key=int)
        
        if unique_ids:
            # Determine proposal type
            proposal_type = "Discussion" if "discussion" in prompt.lower() else "ReferendumV2"
            
            return {
                "data_source": "dynamic",
                "ID": unique_ids,
                "proposal_type": proposal_type,
                "keywords": ""
            }
        else:
            # Extract keywords for Algolia search
            # Remove common stop words and extract meaningful terms
            stop_words = {"tell", "me", "about", "the", "a", "an", "and", "or", "but", "in", "on", "at", "to", "for", "of", "with", "by"}
            words = re.findall(r'\b\w+\b', prompt.lower())
            keywords = [word for word in words if word not in stop_words and len(word) > 2]
            
            return {
                "data_source": "algolia",
                "ID": [],
                "proposal_type": "",
                "keywords": " ".join(keywords[:5])  # Limit to top 5 keywords
            }

    async def route_request(self, prompt: str) -> Dict[str, Any]:
        """
        Routes the request based on prompt analysis using Gemini or fallback logic.
        
        Args:
            prompt: User's natural language prompt
            
        Returns:
            Dict with routing information: data_source, ID, proposal_type, keywords
        """
        logger.info(f"Routing request for prompt: {prompt}")
        
        if not self.client:
            logger.info("Using fallback routing logic")
            return self._fallback_routing_logic(prompt)
        
        try:
            routing_prompt = f"""
            Analyze the following user prompt and determine the routing strategy.

            User Prompt: "{prompt}"

            ROUTING RULES:
            1. DYNAMIC - If the prompt contains specific proposal IDs, referenda numbers, or discussion IDs:
               - Examples: "proposal ID 1679", "proposal 1622", "referenda 1622", "referendum 1622", "discussion 1104"
               - Look for patterns like: number + (proposal|referenda|referendum|discussion) OR (proposal|referenda|referendum|discussion) + number
               
            2. ALGOLIA - If the prompt is asking about topics, keywords, or general searches:
               - Examples: "Tell me about clarys proposal", "subwallet development proposal", "treasury proposals about AI", "AI proposals"
               - Extract meaningful keywords for search

            IMPORTANT INSTRUCTIONS:
            - Extract ALL proposal IDs mentioned in the prompt
            - For proposal type: use "Discussion" if "discussion" is mentioned, otherwise use "ReferendumV2"
            - For keywords: extract 2-5 most relevant search terms, ignore stop words
            - Return ONLY a valid JSON object, no other text

            RESPONSE FORMAT (JSON only):
            {{
                "data_source": "dynamic" or "algolia",
                "ID": [list of extracted IDs as strings] or [],
                "proposal_type": "ReferendumV2" or "Discussion" or "",
                "keywords": "extracted keywords" or ""
            }}
            """
            
            response = await self._safe_gemini_call(routing_prompt)
            
            # Try to parse JSON response
            import json
            try:
                # Clean response - remove any markdown formatting
                clean_response = response.strip()
                if clean_response.startswith('```json'):
                    clean_response = clean_response[7:]
                if clean_response.endswith('```'):
                    clean_response = clean_response[:-3]
                clean_response = clean_response.strip()
                
                routing_result = json.loads(clean_response)
                
                # Validate and clean the result
                valid_result = {
                    "data_source": routing_result.get("data_source", "algolia"),
                    "ID": routing_result.get("ID", []),
                    "proposal_type": routing_result.get("proposal_type", ""),
                    "keywords": routing_result.get("keywords", "")
                }
                
                logger.info(f"Gemini routing result: {valid_result}")
                return valid_result
                
            except json.JSONDecodeError as e:
                logger.error(f"Failed to parse Gemini routing response as JSON: {e}")
                logger.info("Falling back to regex-based routing")
                return self._fallback_routing_logic(prompt)
                
        except Exception as e:
            logger.error(f"Error in Gemini routing: {str(e)}")
            logger.info("Falling back to regex-based routing")
            return self._fallback_routing_logic(prompt)

    async def search_algolia(self, keywords: str, num_results: int = 10) -> List[Dict[str, Any]]:
        """
        Search Algolia with the given keywords.
        
        Args:
            keywords: Search keywords
            num_results: Number of results to return
            
        Returns:
            List of formatted search results
        """
        logger.info(f"Searching Algolia for keywords: {keywords}")
        
        try:
            # Import here to avoid circular imports
            from app.services.algolia import search_posts
            # Use the async search function
            raw_results = await search_posts(keywords, num_results)
            formatted_results = raw_results  # search_posts already returns formatted results
            
            logger.info(f"Algolia search returned {len(formatted_results)} results")
            return formatted_results
            
        except Exception as e:
            logger.error(f"Error searching Algolia: {str(e)}")
            return []

    async def process_routed_request(self, prompt: str) -> Dict[str, Any]:
        """
        Complete routing and processing pipeline.
        
        Args:
            prompt: User's natural language prompt
            
        Returns:
            Dict with routing info and search results (for Algolia) or empty (for dynamic)
        """
        routing_result = await self.route_request(prompt)
        
        if routing_result["data_source"] == "algolia" and routing_result["keywords"]:
            # Perform Algolia search
            search_results = await self.search_algolia(routing_result["keywords"])
            routing_result["search_results"] = search_results
        else:
            routing_result["search_results"] = []
        
        return routing_result

# Global instance
routing_service = RoutingService() 