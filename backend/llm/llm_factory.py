from llm.openrouter_client import OpenRouterClient


class LLMFactory:

    @staticmethod
    def create(
        provider: str = "openrouter",
    ):

        if provider == "openrouter":
            return OpenRouterClient()

        raise ValueError(
            f"Unsupported LLM provider: {provider}"
        )