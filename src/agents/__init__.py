"""
Agents Module

This module contains different AI agents for the chatbot system.
Each agent is specialized for specific tasks and capabilities.
"""

from .manager_agent import ManagerAgent
from .base_agent import BaseAgent

__all__ = ["ManagerAgent", "BaseAgent"]