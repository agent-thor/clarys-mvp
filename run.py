#!/usr/bin/env python3
"""
Run script for the Multi-Agent ID & Link Extractor API
"""

import os
import uvicorn
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

if __name__ == "__main__":
    # Get configuration from environment variables
    host = os.getenv("API_HOST", "0.0.0.0")
    port = int(os.getenv("API_PORT", "8000"))
    log_level = os.getenv("LOG_LEVEL", "info").lower()
    
    print(f"Starting Multi-Agent ID & Link Extractor API on {host}:{port}")
    print(f"Log level: {log_level}")
    
    # Run the server
    uvicorn.run(
        "app.main:app",
        host=host,
        port=port,
        log_level=log_level,
        reload=True if os.getenv("ENVIRONMENT") == "development" else False
    ) 