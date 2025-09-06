"""
Agents Module

This module contains different AI agents for the chatbot system.
Each agent is specialized for specific tasks and capabilities.
"""

from .manager_agent import create_manager_agent, get_manager_model_info

__all__ = ["create_manager_agent", "get_manager_model_info"]