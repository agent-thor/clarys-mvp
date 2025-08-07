import pytest
import asyncio
from app.agents.llm_extractor_agent import LLMExtractorAgent
from app.agents.regex_extractor_agent import RegexExtractorAgent
from app.services.coordinator_agent import CoordinatorAgent

class TestLLMExtractorAgent:
    
    @pytest.fixture
    def llm_agent(self):
        return LLMExtractorAgent()
    
    @pytest.mark.asyncio
    async def test_extract_ids_basic(self, llm_agent):
        """Test basic ID extraction"""
        prompt = "Compare ID123 and ID456"
        result = await llm_agent.process(prompt)
        
        assert "ids" in result
        assert isinstance(result["ids"], list)
        # Should find at least one ID
        assert len(result["ids"]) > 0
    
    @pytest.mark.asyncio
    async def test_extract_ids_mixed_content(self, llm_agent):
        """Test ID extraction with mixed content"""
        prompt = "Compare ID123 and https://example.com"
        result = await llm_agent.process(prompt)
        
        assert "ids" in result
        assert isinstance(result["ids"], list)
        # Should extract ID123 but not the URL
        ids = result["ids"]
        assert any("ID123" in id_val for id_val in ids)
    
    @pytest.mark.asyncio
    async def test_extract_no_ids(self, llm_agent):
        """Test when no IDs are present"""
        prompt = "This is just regular text without any identifiers"
        result = await llm_agent.process(prompt)
        
        assert "ids" in result
        assert isinstance(result["ids"], list)

class TestRegexExtractorAgent:
    
    @pytest.fixture
    def regex_agent(self):
        return RegexExtractorAgent()
    
    @pytest.mark.asyncio
    async def test_extract_urls_basic(self, regex_agent):
        """Test basic URL extraction"""
        prompt = "Check out https://example.com and https://test.org"
        result = await regex_agent.process(prompt)
        
        assert "links" in result
        assert isinstance(result["links"], list)
        assert "https://example.com" in result["links"]
        assert "https://test.org" in result["links"]
    
    @pytest.mark.asyncio
    async def test_extract_single_url(self, regex_agent):
        """Test single URL extraction"""
        prompt = "Visit https://abc.com for more info"
        result = await regex_agent.process(prompt)
        
        assert "links" in result
        assert isinstance(result["links"], list)
        assert "https://abc.com" in result["links"]
    
    @pytest.mark.asyncio
    async def test_extract_no_urls(self, regex_agent):
        """Test when no URLs are present"""
        prompt = "This text has no links at all"
        result = await regex_agent.process(prompt)
        
        assert "links" in result
        assert isinstance(result["links"], list)
        assert len(result["links"]) == 0
    
    @pytest.mark.asyncio
    async def test_extract_mixed_content(self, regex_agent):
        """Test URL extraction with mixed content"""
        prompt = "Compare https://abc.com and ID123"
        result = await regex_agent.process(prompt)
        
        assert "links" in result
        assert isinstance(result["links"], list)
        assert "https://abc.com" in result["links"]

class TestCoordinatorAgent:
    
    @pytest.fixture
    def coordinator(self):
        return CoordinatorAgent()
    
    @pytest.mark.asyncio
    async def test_coordinate_ids_only(self, coordinator):
        """Test coordination with IDs only"""
        prompt = "Compare ID123 and ID456"
        result = await coordinator.process_prompt(prompt)
        
        assert hasattr(result, 'ids')
        assert hasattr(result, 'links')
        assert isinstance(result.ids, list)
        assert isinstance(result.links, list)
        assert len(result.ids) > 0
        assert len(result.links) == 0
    
    @pytest.mark.asyncio
    async def test_coordinate_links_only(self, coordinator):
        """Test coordination with links only"""
        prompt = "How is https://abc.com different from https://xyz.com?"
        result = await coordinator.process_prompt(prompt)
        
        assert hasattr(result, 'ids')
        assert hasattr(result, 'links')
        assert isinstance(result.ids, list)
        assert isinstance(result.links, list)
        assert len(result.links) > 0
    
    @pytest.mark.asyncio
    async def test_coordinate_mixed_content(self, coordinator):
        """Test coordination with both IDs and links"""
        prompt = "Compare https://abc.com and ID123"
        result = await coordinator.process_prompt(prompt)
        
        assert hasattr(result, 'ids')
        assert hasattr(result, 'links')
        assert isinstance(result.ids, list)
        assert isinstance(result.links, list)
        # Should have both IDs and links
        assert len(result.ids) > 0
        assert len(result.links) > 0
        assert "https://abc.com" in result.links
    
    @pytest.mark.asyncio
    async def test_coordinate_empty_input(self, coordinator):
        """Test coordination with empty or minimal input"""
        prompt = "Hello"
        result = await coordinator.process_prompt(prompt)
        
        assert hasattr(result, 'ids')
        assert hasattr(result, 'links')
        assert isinstance(result.ids, list)
        assert isinstance(result.links, list) 