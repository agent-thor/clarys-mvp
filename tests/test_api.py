import pytest
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)

class TestAPI:
    
    def test_root_endpoint(self):
        """Test the root endpoint"""
        response = client.get("/")
        assert response.status_code == 200
        data = response.json()
        assert "message" in data
        assert "version" in data
    
    def test_health_endpoint(self):
        """Test the health check endpoint"""
        response = client.get("/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
    
    def test_extract_ids_only(self):
        """Test extraction with IDs only"""
        payload = {"prompt": "Compare ID123 and ID456"}
        response = client.post("/extract", json=payload)
        
        assert response.status_code == 200
        data = response.json()
        assert "ids" in data
        assert "links" in data
        assert isinstance(data["ids"], list)
        assert isinstance(data["links"], list)
        assert len(data["ids"]) > 0
        assert len(data["links"]) == 0
    
    def test_extract_links_only(self):
        """Test extraction with links only"""
        payload = {"prompt": "How is https://abc.com different from https://xyz.com?"}
        response = client.post("/extract", json=payload)
        
        assert response.status_code == 200
        data = response.json()
        assert "ids" in data
        assert "links" in data
        assert isinstance(data["ids"], list)
        assert isinstance(data["links"], list)
        assert len(data["links"]) > 0
        assert "https://abc.com" in data["links"]
        assert "https://xyz.com" in data["links"]
    
    def test_extract_mixed_content(self):
        """Test extraction with both IDs and links"""
        payload = {"prompt": "Compare https://abc.com and ID123"}
        response = client.post("/extract", json=payload)
        
        assert response.status_code == 200
        data = response.json()
        assert "ids" in data
        assert "links" in data
        assert isinstance(data["ids"], list)
        assert isinstance(data["links"], list)
        assert len(data["ids"]) > 0
        assert len(data["links"]) > 0
        assert "https://abc.com" in data["links"]
    
    def test_extract_empty_prompt(self):
        """Test extraction with empty prompt"""
        payload = {"prompt": ""}
        response = client.post("/extract", json=payload)
        
        # Should return validation error for empty prompt
        assert response.status_code == 422
    
    def test_extract_no_content(self):
        """Test extraction with text that has no IDs or links"""
        payload = {"prompt": "This is just regular text with no identifiers or URLs"}
        response = client.post("/extract", json=payload)
        
        assert response.status_code == 200
        data = response.json()
        assert "ids" in data
        assert "links" in data
        assert isinstance(data["ids"], list)
        assert isinstance(data["links"], list)
    
    def test_extract_invalid_json(self):
        """Test with invalid JSON payload"""
        response = client.post("/extract", json={"invalid": "field"})
        
        # Should return validation error
        assert response.status_code == 422 