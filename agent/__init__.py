"""Agent package exports.

Provides convenient access to the core Agent class and its configuration
object via: `from agent import Agent, AgentConfig`.
"""

from .agent import Agent
from .config import AgentConfig

__all__ = [
	"Agent",
	"AgentConfig",
]
