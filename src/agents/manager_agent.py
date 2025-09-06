"""
Manager Agent

This module implements the main manager agent that coordinates with other specialized agents
and uses LiteLLMModel with GPT-4o-mini for general conversation handling.
"""

from smolagents import CodeAgent, LiteLLMModel
from typing import Optional, Dict, Any, List
import os
import logging

logger = logging.getLogger(__name__)

def create_manager_agent(
    api_key: Optional[str] = None,
    tools: Optional[List] = None,
    managed_agents: Optional[List] = None,
    max_steps: int = 5,
    verbosity_level: int = 1
) -> CodeAgent:
    """
    Create the manager agent with vision capabilities and coordination of specialized agents.
    
    Args:
        api_key: Optional OpenAI API key. If not provided, will use OPENAI_API_KEY env var.
        tools: List of tools available to the manager agent
        managed_agents: List of specialized agents that this manager can coordinate
        max_steps: Maximum number of steps for agent execution
        verbosity_level: Logging verbosity level
        
    Returns:
        CodeAgent: The configured manager agent
        
    Raises:
        ValueError: If API key is not provided
        Exception: If agent initialization fails
    """
    # Get API key from parameter or environment
    openai_api_key = api_key or os.getenv("OPENAI_API_KEY")
    
    if not openai_api_key:
        raise ValueError(
            "OpenAI API key is required. Set OPENAI_API_KEY environment variable "
            "or pass api_key parameter."
        )
    
    try:
        # Initialize LiteLLMModel with GPT-4o-mini
        manager_model = LiteLLMModel(
            model_id="gpt-4o-mini",  # Cost-effective GPT-4o variant
            api_key=openai_api_key,
            temperature=0.7,  # Balanced creativity/consistency
            max_tokens=2000,  # Reasonable response length
            requests_per_minute=50  # Rate limiting
        )
        
        # Create the manager agent with coordination capabilities
        manager_agent = CodeAgent(
            tools=tools or [],  # Tools available to the manager
            managed_agents=managed_agents or [],  # Specialized agents to coordinate
            model=manager_model,
            max_steps=max_steps,
            verbosity_level=verbosity_level
        )
        
        logger.info("Manager Agent created successfully with GPT-4o-mini")
        return manager_agent
        
    except Exception as e:
        logger.error(f"Failed to create Manager Agent: {e}")
        raise

def get_manager_model_info() -> Dict[str, Any]:
    """
    Get information about the manager agent's model configuration.
    
    Returns:
        Dict[str, Any]: Model information
    """
    return {
        "model_id": "gpt-4o-mini",
        "provider": "OpenAI",
        "framework": "LiteLLM",
        "temperature": 0.7,
        "max_tokens": 2000,
        "requests_per_minute": 50,
        "capabilities": [
            "text_generation",
            "code_execution", 
            "agent_coordination",
            "tool_usage"
        ]
    }