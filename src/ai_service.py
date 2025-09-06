"""
AI Service Module

This module provides the core AI functionality using smolagents for question-answering.
It implements a simple agent that can process text input and return responses.
"""

from smolagents import CodeAgent, InferenceClientModel
from typing import Optional
import logging
import os

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class AIService:
    """
    AI Service class that handles question-answering using smolagents.
    
    This service provides a simple interface for processing text queries
    and returning AI-generated responses using the CodeAgent from smolagents.
    """
    
    def __init__(self, model_id: Optional[str] = None):
        """
        Initialize the AI service with a smolagents CodeAgent.
        
        Args:
            model_id: Optional model ID to use. Defaults to smolagents default.
        """
        try:
            # Initialize the model
            if model_id:
                self.model = InferenceClientModel(model_id=model_id)
            else:
                # Use default model (Qwen/Qwen2.5-Coder-32B-Instruct)
                self.model = InferenceClientModel()
            
            # Create agent with minimal configuration for basic Q&A
            self.agent = CodeAgent(
                tools=[],  # Start with no tools for basic functionality
                model=self.model,
                max_steps=3,  # Limit steps for simple Q&A
                verbosity_level=1  # Moderate verbosity
            )
            
            logger.info("AI Service initialized successfully")
            
        except Exception as e:
            logger.error(f"Failed to initialize AI Service: {e}")
            raise
    
    def process_query(self, query: str) -> str:
        """
        Process a text query and return an AI-generated response.
        
        Args:
            query: The input question or statement to process
            
        Returns:
            str: The AI-generated response
            
        Raises:
            ValueError: If query is empty or None
            Exception: If AI processing fails
        """
        if not query or not query.strip():
            raise ValueError("Query cannot be empty")
        
        try:
            logger.info(f"Processing query: {query[:100]}...")
            
            # Run the agent with the query
            result = self.agent.run(query)
            
            logger.info("Query processed successfully")
            return str(result)
            
        except Exception as e:
            logger.error(f"Failed to process query: {e}")
            raise Exception(f"AI processing failed: {e}")
    
    def health_check(self) -> dict:
        """
        Perform a basic health check of the AI service.
        
        Returns:
            dict: Health status information
        """
        try:
            # Test with a simple query
            test_result = self.process_query("What is 2+2?")
            
            return {
                "status": "healthy",
                "model_available": True,
                "test_query_success": True,
                "agent_initialized": self.agent is not None
            }
        except Exception as e:
            return {
                "status": "unhealthy",
                "model_available": False,
                "test_query_success": False,
                "agent_initialized": self.agent is not None,
                "error": str(e)
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
        model_id = os.getenv("AI_MODEL_ID")  # Optional custom model
        _ai_service_instance = AIService(model_id=model_id)
    
    return _ai_service_instance