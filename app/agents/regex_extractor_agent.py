import re
from typing import Dict, Any, List
from app.agents.base_agent import BaseAgent

class RegexExtractorAgent(BaseAgent):
    """Agent that uses regex to extract URLs from text"""
    
    def __init__(self):
        super().__init__("Regex_Extractor")
        
        # Comprehensive URL regex pattern
        self.url_pattern = re.compile(
            r'http[s]?://(?:[a-zA-Z]|[0-9]|[$-_@.&+]|[!*\\(\\),]|(?:%[0-9a-fA-F][0-9a-fA-F]))+'
        )
        
        # Alternative patterns for different URL formats
        self.url_patterns = [
            # Standard HTTP/HTTPS URLs
            re.compile(r'https?://(?:[-\w.])+(?:[:\d]+)?(?:/(?:[\w/_.])*)?(?:\?(?:[\w&=%.])*)?(?:#(?:\w)*)?'),
            # URLs without protocol
            re.compile(r'(?:www\.)?[a-zA-Z0-9](?:[a-zA-Z0-9-]{0,61}[a-zA-Z0-9])?(?:\.[a-zA-Z0-9](?:[a-zA-Z0-9-]{0,61}[a-zA-Z0-9])?)*\.[a-zA-Z]{2,}'),
            # Simple domain pattern
            re.compile(r'\b[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}\b')
        ]
    
    async def process(self, input_data: str) -> Dict[str, Any]:
        """Extract URLs from the input text using regex"""
        self.log_info(f"Processing text for URL extraction: {input_data}")
        
        try:
            urls = set()
            
            # Primary pattern for complete HTTP/HTTPS URLs
            primary_pattern = re.compile(r'https?://[^\s<>"\']+')
            matches = primary_pattern.findall(input_data)
            
            for match in matches:
                # Clean up the URL (remove trailing punctuation)
                cleaned_url = re.sub(r'[.,;!?]+$', '', match)
                if self._validate_url(cleaned_url):
                    urls.add(cleaned_url)
            
            # Only look for domain patterns if no HTTP URLs were found
            if not urls:
                for pattern in self.url_patterns[1:]:  # Skip the first pattern (HTTP URLs)
                    matches = pattern.findall(input_data)
                    for match in matches:
                        # Add protocol if missing and it's a valid domain
                        if not match.startswith(('http://', 'https://')):
                            if self._is_likely_url(match):
                                candidate_url = f"https://{match}"
                                if self._validate_url(candidate_url):
                                    urls.add(candidate_url)
                        else:
                            if self._validate_url(match):
                                urls.add(match)
            
            validated_urls = list(urls)
            self.log_info(f"Extracted URLs: {validated_urls}")
            return {"links": validated_urls}
            
        except Exception as e:
            self.log_error(f"Error in regex extraction: {str(e)}")
            return {"links": []}
    
    def _is_likely_url(self, text: str) -> bool:
        """Check if text is likely a URL"""
        # Must contain at least one dot and have valid domain structure
        if '.' not in text:
            return False
        
        # Should not be just a file extension
        if text.startswith('.') or text.endswith('.'):
            return False
        
        # Should have reasonable length
        if len(text) < 4 or len(text) > 200:
            return False
        
        # Should contain valid domain characters
        valid_chars = set('abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789.-_/')
        if not all(c in valid_chars for c in text):
            return False
        
        return True
    
    def _validate_url(self, url: str) -> bool:
        """Enhanced URL validation"""
        try:
            # Must start with http or https
            if not url.startswith(('http://', 'https://')):
                return False
            
            # Must have reasonable length
            if len(url) < 10 or len(url) > 500:
                return False
            
            # Split URL to get domain part
            url_parts = url.split('://', 1)
            if len(url_parts) != 2:
                return False
            
            domain_and_path = url_parts[1]
            
            # Must contain a domain with at least one dot
            if '.' not in domain_and_path:
                return False
            
            # Domain should be the first part (before any path)
            domain_part = domain_and_path.split('/')[0]
            
            # Basic domain validation
            if not domain_part or domain_part.startswith('.') or domain_part.endswith('.'):
                return False
            
            # Should have at least one dot in domain
            if '.' not in domain_part:
                return False
            
            return True
            
        except Exception:
            return False 