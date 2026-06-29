"""
Arbiter — GUI entry point.

Run instead of main.py to get the desktop interface:
    python main_gui.py

Requires: pip install PyQt6
"""

from config.config_loader import cfg
from tools.registry import ToolRegistry
from tools.loader import load_tools
from models.llm_router import LLMRouter
from agent.agent_loop import AgentLoop
from interface.gui_interface import launch_gui


def main():
    registry = ToolRegistry()
    load_tools(registry)
    llm   = LLMRouter(registry)
    agent = AgentLoop(llm, registry)
    launch_gui(agent)


if __name__ == "__main__":
    main()
