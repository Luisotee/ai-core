"""
Manager Agent

This module implements the main manager agent that coordinates with other agents
and uses LiteLLMModel with GPT-4o-mini for general conversation handling.
"""

from smolagents import CodeAgent, LiteLLMModel
from typing import Optional, Dict, Any
import os
from .base_agent import BaseAgent

class ManagerAgent(BaseAgent):
    """
    Manager Agent that handles general queries and coordinates with other specialized agents.
    
    Uses GPT-4o-mini via LiteLLMModel for cost-effective and efficient responses.
    """
    
    def __init__(self, api_key: Optional[str] = None):
        """
        Initialize the Manager Agent with LiteLLMModel.
        
        Args:
            api_key: Optional OpenAI API key. If not provided, will use OPENAI_API_KEY env var.
        """
        super().__init__(
            name="ManagerAgent",
            description="Main conversational agent using GPT-4o-mini for general queries"
        )
        
        # Get API key from parameter or environment
        self.api_key = api_key or os.getenv("OPENAI_API_KEY")
        
        if not self.api_key:
            raise ValueError(
                "OpenAI API key is required. Set OPENAI_API_KEY environment variable "
                "or pass api_key parameter."
            )
        
        try:
            # Initialize LiteLLMModel with GPT-4o-mini
            self.model = LiteLLMModel(
                model_id="gpt-4o-mini",  # Cost-effective GPT-4o variant
                api_key=self.api_key,
                temperature=0.7,  # Balanced creativity/consistency
                max_tokens=2000,  # Reasonable response length
                requests_per_minute=50  # Rate limiting
            )
            
            # Create the smolagents CodeAgent with minimal tools for basic Q&A
            self.agent = CodeAgent(
                tools=[],  # Start with no tools for basic functionality
                model=self.model,
                max_steps=3,  # Limit steps for conversation
                verbosity_level=1  # Moderate verbosity
            )
            
            self.logger.info("Manager Agent initialized successfully with GPT-4o-mini")
            
        except Exception as e:
            self.logger.error(f"Failed to initialize Manager Agent: {e}")
            raise
    
    def process_query(self, query: str, context: Optional[Dict[str, Any]] = None) -> str:
        """
        Process a text query using the GPT-4o-mini powered agent.
        
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
                if context.get("user_id"):
                    enhanced_query = f"[User: {context['user_id']}] {query}"
                if context.get("conversation_context"):
                    enhanced_query = f"{context['conversation_context']}\n\nUser: {enhanced_query}"
            
            self.logger.info(f"Processing query for {self.name}: {query[:100]}...")
            
            # Run the agent with the enhanced query
            result = self.agent.run(enhanced_query)
            
            self.logger.info("Query processed successfully")
            return str(result)
            
        except Exception as e:
            self.logger.error(f"Failed to process query: {e}")
            raise Exception(f"Manager Agent processing failed: {e}")
    
    def health_check(self) -> Dict[str, Any]:
        """
        Perform a health check of the Manager Agent.
        
        Returns:
            Dict[str, Any]: Health status information
        """
        try:
            # Test with a simple query
            test_result = self.process_query("Hello, are you working properly?")
            
            return {
                "status": "healthy",
                "agent_name": self.name,
                "model": "gpt-4o-mini",
                "model_available": True,
                "test_query_success": True,
                "agent_initialized": self.agent is not None,
                "api_key_configured": bool(self.api_key)
            }
        except Exception as e:
            return {
                "status": "unhealthy",
                "agent_name": self.name,
                "model": "gpt-4o-mini",
                "model_available": False,
                "test_query_success": False,
                "agent_initialized": self.agent is not None,
                "api_key_configured": bool(self.api_key),
                "error": str(e)
            }
    
    def get_model_info(self) -> Dict[str, Any]:
        """
        Get information about the underlying model.
        
        Returns:
            Dict[str, Any]: Model information
        """
        return {
            "model_id": "gpt-4o-mini",
            "provider": "OpenAI",
            "framework": "LiteLLM",
            "temperature": 0.7,
            "max_tokens": 2000,
            "requests_per_minute": 50
        }