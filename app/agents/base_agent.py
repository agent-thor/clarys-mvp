from abc import ABC, abstractmethod
from typing import Any, Dict
import logging

class BaseAgent(ABC):
    """Base class for all agents in the multi-agent system"""
    
    def __init__(self, name: str):
        self.name = name
        self.logger = logging.getLogger(f"agent.{name}")
    
    @abstractmethod
    async def process(self, input_data: str) -> Dict[str, Any]:
        """Process input data and return structured output"""
        pass
    
    def log_info(self, message: str):
        """Log info message with agent name"""
        self.logger.info(f"[{self.name}] {message}")
    
    def log_error(self, message: str):
        """Log error message with agent name"""
        self.logger.error(f"[{self.name}] {message}") 