"""
AI Service Module

This module provides the core AI functionality using a manager agent that coordinates
with specialized agents for different tasks.
"""

from typing import Optional, Dict, Any
import logging
import os
from smolagents import CodeAgent
from .agents import create_manager_agent
from .database import get_database_manager

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class AIService:
    """
    AI Service class that uses a manager agent to coordinate specialized agents.
    
    The manager agent can delegate tasks to specialized agents while handling
    general conversation and coordination.
    """
    
    def __init__(self, openai_api_key: Optional[str] = None, max_steps: int = 5):
        """
        Initialize the AI service with a manager agent.
        
        Args:
            openai_api_key: Optional OpenAI API key for the manager agent
            max_steps: Maximum steps for agent execution
        """
        try:
            # Initialize database manager
            self.db_manager = get_database_manager()
            
            # Create the manager agent with coordination capabilities
            self.manager_agent: CodeAgent = create_manager_agent(
                api_key=openai_api_key,
                tools=[],  # Will be populated with tools as needed
                managed_agents=[],  # Will be populated with specialized agents
                max_steps=max_steps,
                verbosity_level=1
            )
            
            # Store specialized agents that the manager can coordinate
            self.specialized_agents = []
            
            logger.info("AI Service initialized successfully with manager agent and database")
            
        except Exception as e:
            logger.error(f"Failed to initialize AI Service: {e}")
            raise
    
    def process_query(self, query: str, context: Optional[Dict[str, Any]] = None) -> str:
        """
        Process a text query using the manager agent.
        
        Args:
            query: The input question or statement to process
            context: Optional context information (user_id, conversation history, etc.)
            
        Returns:
            str: The AI-generated response
            
        Raises:
            ValueError: If query is empty or None
            Exception: If AI processing fails
        """
        if not query or not query.strip():
            raise ValueError("Query cannot be empty")
        
        try:
            # Add context to query if provided
            enhanced_query = query
            if context:
                context_parts = []
                if context.get("user_id"):
                    context_parts.append(f"User ID: {context['user_id']}")
                if context.get("conversation_context"):
                    context_parts.append(f"Context: {context['conversation_context']}")
                
                if context_parts:
                    enhanced_query = f"[{', '.join(context_parts)}]\n\n{query}"
            
            logger.info(f"Processing query: {query[:100]}...")
            
            # Run the manager agent with the query
            result = self.manager_agent.run(enhanced_query)
            
            logger.info("Query processed successfully")
            return str(result)
            
        except Exception as e:
            logger.error(f"Failed to process query: {e}")
            raise Exception(f"AI processing failed: {e}")
    
    def health_check(self) -> Dict[str, Any]:
        """
        Perform a health check of the AI service.
        
        Returns:
            Dict[str, Any]: Health status information
        """
        try:
            # Test database health
            db_health = self.db_manager.health_check()
            
            # Test with a simple query
            self.process_query("Hello, are you working properly?")
            
            return {
                "status": "healthy",
                "service": "ai-service",
                "manager_agent": {
                    "status": "healthy",
                    "model": "gpt-4o-mini",
                    "test_query_success": True,
                    "agent_initialized": self.manager_agent is not None
                },
                "database": db_health,
                "specialized_agents_count": len(self.specialized_agents)
            }
        except Exception as e:
            # Get database health even if AI test fails
            try:
                db_health = self.db_manager.health_check()
            except:
                db_health = {"status": "unknown", "error": "Could not perform database health check"}
            
            return {
                "status": "unhealthy",
                "service": "ai-service", 
                "manager_agent": {
                    "status": "unhealthy",
                    "model": "gpt-4o-mini",
                    "test_query_success": False,
                    "agent_initialized": self.manager_agent is not None,
                    "error": str(e)
                },
                "database": db_health,
                "specialized_agents_count": len(self.specialized_agents)
            }
    
    def add_specialized_agent(self, agent: CodeAgent, name: str) -> None:
        """
        Add a specialized agent that the manager can coordinate.
        
        Args:
            agent: The specialized agent to add
            name: Name identifier for the agent
        """
        self.specialized_agents.append({"name": name, "agent": agent})
        
        # Update the manager agent with the new specialized agent
        self.manager_agent = create_manager_agent(
            tools=getattr(self.manager_agent, 'tools', []),
            managed_agents=[item["agent"] for item in self.specialized_agents],
            max_steps=getattr(self.manager_agent, 'max_steps', 5)
        )
        
        logger.info(f"Added specialized agent: {name}")
    
    def get_service_info(self) -> Dict[str, Any]:
        """
        Get information about the AI service configuration.
        
        Returns:
            Dict[str, Any]: Service information
        """
        return {
            "service": "ai-service",
            "manager_model": "gpt-4o-mini",
            "specialized_agents": [
                {"name": item["name"], "type": type(item["agent"]).__name__} 
                for item in self.specialized_agents
            ],
            "capabilities": [
                "text_generation",
                "conversation_handling", 
                "agent_coordination",
                "context_awareness"
            ]
        }

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
        max_steps = int(os.getenv("AI_MAX_STEPS", "5"))
        _ai_service_instance = AIService(
            openai_api_key=openai_api_key,
            max_steps=max_steps
        )
    
    return _ai_service_instance