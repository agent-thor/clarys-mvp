import json
import os
import asyncio
from typing import Dict, Any, List
from app.agents.base_agent import BaseAgent
from app.services.gemini import GeminiClient

class LLMExtractorAgent(BaseAgent):
    """Agent that uses Gemini LLM to extract IDs from natural language prompts"""
    
    def __init__(self):
        super().__init__("LLM_Extractor")
        
        # Initialize Gemini client with fallback
        try:
            self.client = GeminiClient(model_name="gemini-2.5-flash-lite", timeout=15)
            self.log_info("Gemini client initialized successfully")
            self.use_gemini = True
        except Exception as e:
            self.log_error(f"Failed to initialize Gemini client: {str(e)}")
            self.client = None
            self.use_gemini = False
    
    async def process(self, input_data: str) -> Dict[str, Any]:
        """Extract IDs from the input prompt using Gemini LLM"""
        self.log_info(f"Processing prompt for ID extraction: {input_data}")
        
        try:
            if not self.use_gemini or self.client is None:
                # Use enhanced rule-based extraction
                return await self._fallback_extraction(input_data)
            
            # Try Gemini extraction with proper error handling
            try:
                # Create the prompt for ID extraction
                extraction_prompt = f"""You are an expert at extracting custom identifiers (IDs) from text. 

IMPORTANT RULES:
1. Extract standalone IDs/numbers that are NOT part of URLs
2. If text contains URLs like "https://example.com/referenda/1234", do NOT extract "1234" as an ID
3. Only extract IDs that appear as standalone identifiers (e.g., "proposal 1679", "ID123")

Extract IDs that are:
- Alphanumeric codes (e.g., ID123, USER456, PROD789)  
- Standalone proposal numbers (e.g., "proposal 1679")
- Custom identifiers that are NOT embedded in URLs

Return ONLY a JSON array of the extracted IDs. If no standalone IDs are found, return an empty array.
Do NOT extract numbers or identifiers that are part of URLs.

Text to analyze: {input_data}

Response (JSON array only):"""
                
                # Use a simpler approach without signals/timeouts that cause threading issues
                response = self._safe_gemini_call(extraction_prompt)
                
                if response and "Error" not in response:
                    # Parse the response
                    try:
                        # Clean up the response to extract JSON
                        content = response.strip()
                        
                        # Try to find JSON array in the response
                        if '[' in content and ']' in content:
                            start_idx = content.find('[')
                            end_idx = content.rfind(']') + 1
                            json_str = content[start_idx:end_idx]
                            ids = json.loads(json_str)
                            
                            if not isinstance(ids, list):
                                ids = []
                        else:
                            # If no JSON array found, try to parse the entire response
                            ids = json.loads(content)
                            if not isinstance(ids, list):
                                ids = []
                                
                    except json.JSONDecodeError:
                        self.log_error(f"Failed to parse Gemini response as JSON: {response}")
                        # Try to extract IDs manually from response
                        ids = self._extract_ids_from_text(response)
                    
                    self.log_info(f"Extracted IDs via Gemini: {ids}")
                    return {"ids": ids}
                else:
                    raise Exception(f"Gemini API error: {response}")
                    
            except Exception as gemini_error:
                self.log_error(f"Gemini extraction failed: {str(gemini_error)}")
                # Fallback to rule-based extraction
                return await self._fallback_extraction(input_data)
            
        except Exception as e:
            self.log_error(f"Error in extraction process: {str(e)}")
            # Final fallback to rule-based extraction
            return await self._fallback_extraction(input_data)
    
    def _safe_gemini_call(self, prompt: str) -> str:
        """Make a safe Gemini API call without signal-based timeouts"""
        try:
            # Create a simple client without timeout signals
            import os
            from google import genai
            
            api_key = os.getenv("GEMINI_API_KEY")
            if not api_key:
                raise Exception("GEMINI_API_KEY not found")
            
            client = genai.Client(api_key=api_key)
            response = client.models.generate_content(
                model="gemini-2.5-flash-lite",
                contents=prompt
            )
            return response.text
            
        except Exception as e:
            self.log_error(f"Safe Gemini call failed: {str(e)}")
            return f"Error: {str(e)}"
    
    def _extract_ids_from_text(self, text: str) -> List[str]:
        """Extract IDs from text when JSON parsing fails"""
        import re
        
        # Look for quoted strings that might be IDs
        quoted_pattern = r'"([A-Z0-9_]+\d+[A-Z0-9_]*)"'
        matches = re.findall(quoted_pattern, text, re.IGNORECASE)
        
        if matches:
            return matches
        
        # Fallback to basic ID patterns
        id_patterns = [
            r'\b[A-Z]{2,}\d+\b',
            r'\b[A-Z]+\d+[A-Z]*\b',
            r'\b\w*ID\d+\w*\b',
        ]
        
        ids = set()
        for pattern in id_patterns:
            pattern_matches = re.findall(pattern, text, re.IGNORECASE)
            for match in pattern_matches:
                if not match.lower() in ['the', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for']:
                    ids.add(match)
        
        return list(ids)
    
    async def _fallback_extraction(self, text: str) -> Dict[str, Any]:
        """Enhanced fallback rule-based ID extraction when LLM is not available"""
        import re
        
        self.log_info("Using enhanced fallback rule-based ID extraction")
        
        # Check if text contains URLs - if so, be more restrictive about ID extraction
        has_urls = bool(re.search(r'https?://', text, re.IGNORECASE))
        
        ids = set()
        
        if has_urls:
            # More restrictive extraction when URLs are present
            # Only extract IDs that are clearly standalone and not part of URLs
            
            # Look for "proposal X" patterns that are NOT in URLs
            proposal_pattern = r'\bproposal\s+(?:id\s+)?(\d+)(?!\S)'  # "proposal 1679" or "proposal id 1679"
            proposal_matches = re.findall(proposal_pattern, text, re.IGNORECASE)
            for match in proposal_matches:
                # Double check this isn't part of a URL
                if not re.search(rf'https?://[^\s]*{re.escape(match)}', text, re.IGNORECASE):
                    ids.add(match)
            
            # Look for explicit ID patterns that are clearly not URLs
            explicit_id_patterns = [
                r'\b[A-Z]{2,}\d+\b',  # e.g., ID123, USER456
                r'\b[A-Z]+\d+[A-Z]*\b',  # e.g., PROD789A  
                r'\b\w*ID\d+\w*\b',  # e.g., ID123, MyID456
            ]
            
            for pattern in explicit_id_patterns:
                matches = re.findall(pattern, text, re.IGNORECASE)
                for match in matches:
                    # Ensure this ID is not part of a URL
                    if not re.search(rf'https?://[^\s]*{re.escape(match)}', text, re.IGNORECASE):
                        if not match.lower() in ['the', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for']:
                            ids.add(match)
        
        else:
            # Original enhanced extraction for non-URL text
            # First, look for contextual patterns (proposal numbers, etc.)
            proposal_matches = re.findall(r'\bproposal\s+(?:id\s+)?(\d+)', text, re.IGNORECASE)
            for match in proposal_matches:
                ids.add(match)
            
            # Look for "X and Y" patterns where X and Y are numbers
            and_patterns = re.findall(r'\b(\d{3,})\s+and\s+(\d{3,})\b', text, re.IGNORECASE)
            for match_pair in and_patterns:
                ids.add(match_pair[0])
                ids.add(match_pair[1])
            
            # Apply other ID patterns
            id_patterns = [
                r'\b[A-Z]{2,}\d+\b',  # e.g., ID123, USER456
                r'\b[A-Z]+\d+[A-Z]*\b',  # e.g., PROD789A
                r'\b\w*ID\d+\w*\b',  # e.g., ID123, MyID456
                r'\b[A-Z]{1,5}\d{2,}\b',  # e.g., A123, BC4567
                r'\b(\d{3,})\b',  # standalone numbers with 3+ digits (like 1679, 1680)
            ]
            
            for pattern in id_patterns:
                matches = re.findall(pattern, text, re.IGNORECASE)
                for match in matches:
                    if isinstance(match, tuple):
                        # Handle patterns with groups
                        for group in match:
                            if group and group.isdigit() and len(group) >= 3:
                                ids.add(group)
                            elif group and not group.lower() in ['the', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for']:
                                ids.add(group)
                    else:
                        # Handle single matches
                        if match.isdigit() and len(match) >= 3:
                            ids.add(match)
                        elif not match.lower() in ['the', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for']:
                            ids.add(match)
        
        ids_list = list(ids)
        self.log_info(f"Enhanced fallback extracted IDs: {ids_list}")
        return {"ids": ids_list} 