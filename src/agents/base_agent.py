"""
Base Agent Class

This module defines the base agent interface that all specialized agents inherit from.
"""

from abc import ABC, abstractmethod
from typing import Dict, Any, Optional
import logging

logger = logging.getLogger(__name__)

class BaseAgent(ABC):
    """
    Abstract base class for all AI agents in the system.
    
    This class defines the common interface that all agents must implement.
    """
    
    def __init__(self, name: str, description: str):
        """
        Initialize the base agent.
        
        Args:
            name: The name of the agent
            description: Description of what this agent does
        """
        self.name = name
        self.description = description
        self.logger = logging.getLogger(f"{__name__}.{name}")
    
    @abstractmethod
    def process_query(self, query: str, context: Optional[Dict[str, Any]] = None) -> str:
        """
        Process a query and return a response.
        
        Args:
            query: The input query to process
            context: Optional context information
            
        Returns:
            str: The agent's response
        """
        pass
    
    @abstractmethod
    def health_check(self) -> Dict[str, Any]:
        """
        Perform a health check of the agent.
        
        Returns:
            Dict[str, Any]: Health status information
        """
        pass
    
    def get_info(self) -> Dict[str, str]:
        """
        Get basic information about the agent.
        
        Returns:
            Dict[str, str]: Agent information
        """
        return {
            "name": self.name,
            "description": self.description,
            "type": self.__class__.__name__
        }