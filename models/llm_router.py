import json
import requests

from config.config_loader import cfg
from core.exceptions import LLMError
from core.logger import get_logger

logger = get_logger("llm_router")


class LLMRouter:
    """
    LLM abstraction layer.  All connection details come from settings.yaml.
    Supports Ollama (default), and is structured for easy extension to
    OpenAI or Anthropic by swapping _build_payload / _parse_response.
    """

    def __init__(self, registry=None):
        self.registry = registry

        self.provider   = cfg.get("models.provider", "ollama")
        self.base_url   = cfg.get("models.base_url", "http://localhost:11434").rstrip("/")
        self.model      = cfg.get("models.default_model", "llama3:8b")
        self.temperature = cfg.get("models.temperature", 0.2)
        self.max_tokens  = cfg.get("models.max_tokens", 2048)
        self.stream      = cfg.get("models.stream", False)
        self.identity    = cfg.get("models.identity_name", "Arbiter")
        self.forbidden   = cfg.get("models.forbidden_identity_words", [])

        self._endpoint = self._resolve_endpoint()

    # ------------------------------------------------------------------ #
    #  Endpoint resolution                                                 #
    # ------------------------------------------------------------------ #

    def _resolve_endpoint(self) -> str:
        routes = {
            "ollama":    f"{self.base_url}/api/generate",
            "openai":    f"{self.base_url}/v1/chat/completions",
            "anthropic": f"{self.base_url}/v1/messages",
        }
        if self.provider not in routes:
            raise LLMError(f"Unknown provider '{self.provider}'. "
                           "Valid: ollama, openai, anthropic")
        return routes[self.provider]

    # ------------------------------------------------------------------ #
    #  Payload builders (one per provider)                                 #
    # ------------------------------------------------------------------ #

    def _build_payload(self, prompt: str) -> dict:
        if self.provider == "ollama":
            return {
                "model":  self.model,
                "prompt": prompt,
                "stream": self.stream,
                "options": {
                    "temperature": self.temperature,
                    "num_predict": self.max_tokens,
                },
            }
        if self.provider == "openai":
            return {
                "model": self.model,
                "messages": [{"role": "user", "content": prompt}],
                "temperature": self.temperature,
                "max_tokens": self.max_tokens,
            }
        if self.provider == "anthropic":
            return {
                "model": self.model,
                "max_tokens": self.max_tokens,
                "messages": [{"role": "user", "content": prompt}],
            }

    def _parse_response(self, data: dict) -> str:
        if self.provider == "ollama":
            if "response" not in data:
                raise LLMError(f"Unexpected Ollama response: {data}")
            return data["response"]
        if self.provider == "openai":
            return data["choices"][0]["message"]["content"]
        if self.provider == "anthropic":
            return data["content"][0]["text"]
        raise LLMError(f"No response parser for provider '{self.provider}'")

    # ------------------------------------------------------------------ #
    #  Core request                                                        #
    # ------------------------------------------------------------------ #

    def _request(self, prompt: str) -> str:
        payload = self._build_payload(prompt)
        try:
            resp = requests.post(self._endpoint, json=payload, timeout=60)
            resp.raise_for_status()
            data = resp.json()
        except requests.RequestException as exc:
            logger.error("LLM request failed: %s", exc)
            raise LLMError(str(exc)) from exc

        text = self._parse_response(data)
        return self._enforce_identity(text)

    # ------------------------------------------------------------------ #
    #  Public API                                                          #
    # ------------------------------------------------------------------ #

    def chat(self, message: str) -> str:
        """Free-form chat.  Returns natural language string."""
        try:
            return self._request(message)
        except LLMError as exc:
            return f"LLM request failed: {exc}"

    def generate_action(self, context: str) -> dict:
        """
        Structured action generation.
        Returns a dict with keys: action, parameters.
        Falls back to final_answer on any parse failure.
        """
        from agent.tool_prompt_builder import build_tool_prompt
        from agent.prompts import SYSTEM_PROMPT_TOOLS

        tool_desc = self.registry.get_tool_descriptions() if self.registry else []
        tool_prompt = build_tool_prompt(tool_desc)
        full_prompt = SYSTEM_PROMPT_TOOLS + "\n\n" + tool_prompt + "\n\n" + context

        try:
            text = self._request(full_prompt)
        except LLMError as exc:
            return {"action": "final_answer", "parameters": {"answer": str(exc)}}

        return self._parse_action(text)

    # ------------------------------------------------------------------ #
    #  Helpers                                                             #
    # ------------------------------------------------------------------ #

    def _enforce_identity(self, response: str) -> str:
        """Replace forbidden model-name leakage with the agent identity."""
        for word in self.forbidden:
            if word.lower() in response.lower():
                # Case-insensitive replace
                import re
                response = re.sub(re.escape(word), self.identity, response,
                                  flags=re.IGNORECASE)
        return response

    @staticmethod
    def _parse_action(text: str) -> dict:
        """Parse JSON action from LLM output, with fallback."""
        # Strip markdown fences if present
        clean = text.strip().strip("```json").strip("```").strip()
        try:
            action = json.loads(clean)
            if isinstance(action, dict) and "action" in action:
                # Sanitize tool names like "search_web(query)" → "search_web"
                raw_name = action["action"]
                if "(" in raw_name:
                    action["action"] = raw_name.split("(")[0].strip()
                return action
        except (json.JSONDecodeError, ValueError):
            pass
        return {"action": "final_answer", "parameters": {"answer": text}}
