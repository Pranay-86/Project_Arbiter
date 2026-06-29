from config.config_loader import cfg
from tools.registry import ToolRegistry
from tools.loader import load_tools
from models.llm_router import LLMRouter
from agent.agent_loop import AgentLoop
from interface.cli_interface import CLIInterface


def main():
    # 1. Tool system
    registry = ToolRegistry()
    load_tools(registry)

    # 2. LLM — registry passed so generate_action can build tool prompts
    llm = LLMRouter(registry)

    # 3. Agent
    agent = AgentLoop(llm, registry)

    # 4. CLI
    cli = CLIInterface(agent)
    cli.start()


if __name__ == "__main__":
    main()
