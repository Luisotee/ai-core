"""
AI Service Module

This module provides the core AI functionality using multiple specialized agents.
It coordinates between different agents based on query type and context.
"""

from typing import Optional, Dict, Any
import logging
import os
from .agents import ManagerAgent, BaseAgent

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class AIService:
    """
    AI Service class that coordinates multiple specialized agents.
    
    This service routes queries to appropriate agents and manages the overall
    AI functionality of the chatbot system.
    """
    
    def __init__(self, openai_api_key: Optional[str] = None):
        """
        Initialize the AI service with multiple agents.
        
        Args:
            openai_api_key: Optional OpenAI API key for the manager agent
        """
        try:
            # Initialize the manager agent (main conversational agent)
            self.manager_agent = ManagerAgent(api_key=openai_api_key)
            
            # Dictionary to store all available agents
            self.agents: Dict[str, BaseAgent] = {
                "manager": self.manager_agent
            }
            
            # Set the default agent for general queries
            self.default_agent = self.manager_agent
            
            logger.info("AI Service initialized successfully with multiple agents")
            
        except Exception as e:
            logger.error(f"Failed to initialize AI Service: {e}")
            raise
    
    def process_query(self, query: str, context: Optional[Dict[str, Any]] = None, agent_name: Optional[str] = None) -> str:
        """
        Process a text query using the appropriate agent.
        
        Args:
            query: The input question or statement to process
            context: Optional context information (user_id, conversation history, etc.)
            agent_name: Optional specific agent name to use. If None, uses default routing.
            
        Returns:
            str: The AI-generated response
            
        Raises:
            ValueError: If query is empty or None, or if specified agent doesn't exist
            Exception: If AI processing fails
        """
        if not query or not query.strip():
            raise ValueError("Query cannot be empty")
        
        # Select the agent to use
        if agent_name:
            if agent_name not in self.agents:
                raise ValueError(f"Agent '{agent_name}' not found. Available agents: {list(self.agents.keys())}")
            selected_agent = self.agents[agent_name]
        else:
            # Use default agent (manager) for now
            # In the future, this could include intelligent routing logic
            selected_agent = self.default_agent
        
        try:
            logger.info(f"Processing query with {selected_agent.name}: {query[:100]}...")
            
            # Process the query with the selected agent
            result = selected_agent.process_query(query, context)
            
            logger.info(f"Query processed successfully by {selected_agent.name}")
            return result
            
        except Exception as e:
            logger.error(f"Failed to process query with {selected_agent.name}: {e}")
            raise Exception(f"AI processing failed: {e}")
    
    def health_check(self) -> Dict[str, Any]:
        """
        Perform a comprehensive health check of all agents.
        
        Returns:
            Dict[str, Any]: Health status information for all agents
        """
        health_status = {
            "status": "healthy",
            "service": "ai-service",
            "agents": {}
        }
        
        overall_healthy = True
        
        for agent_name, agent in self.agents.items():
            try:
                agent_health = agent.health_check()
                health_status["agents"][agent_name] = agent_health
                
                if agent_health.get("status") != "healthy":
                    overall_healthy = False
                    
            except Exception as e:
                health_status["agents"][agent_name] = {
                    "status": "error",
                    "error": str(e)
                }
                overall_healthy = False
        
        if not overall_healthy:
            health_status["status"] = "degraded"
        
        return health_status
    
    def get_available_agents(self) -> Dict[str, Dict[str, str]]:
        """
        Get information about all available agents.
        
        Returns:
            Dict[str, Dict[str, str]]: Information about each agent
        """
        return {
            name: agent.get_info() 
            for name, agent in self.agents.items()
        }
    
    def add_agent(self, name: str, agent: BaseAgent) -> None:
        """
        Add a new agent to the service.
        
        Args:
            name: Name identifier for the agent
            agent: The agent instance to add
        """
        self.agents[name] = agent
        logger.info(f"Added agent: {name} ({agent.__class__.__name__})")
    
    def get_agent(self, name: str) -> Optional[BaseAgent]:
        """
        Get a specific agent by name.
        
        Args:
            name: Name of the agent to retrieve
            
        Returns:
            Optional[BaseAgent]: The agent instance if found, None otherwise
        """
        return self.agents.get(name)

# Global AI service instance
_ai_service_instance: Optional[AIService] = None

def get_ai_service() -> AIService:
    """
    Get or create the global AI service instance.
    
    Returns:
        AIService: The global AI service instance
    """
    global _ai_service_instance
    
    if _ai_service_instance is None:
        openai_api_key = os.getenv("OPENAI_API_KEY")
        _ai_service_instance = AIService(openai_api_key=openai_api_key)
    
    return _ai_service_instance