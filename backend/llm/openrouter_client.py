import os

from dotenv import load_dotenv
from openai import OpenAI


load_dotenv()


class OpenRouterClient:
    """
    Client for calling LLMs through OpenRouter.
    """

    def __init__(
        self,
        api_key: str | None = None,
        model: str | None = None,
        temperature: float | None = None,
        max_tokens: int | None = None,
    ):

        self.api_key = (
            api_key
            or os.getenv("OPENROUTER_API_KEY")
        )

        if not self.api_key:
            raise ValueError(
                "OPENROUTER_API_KEY is not configured."
            )

        self.base_url = os.getenv(
            "OPENROUTER_BASE_URL",
            "https://openrouter.ai/api/v1",
        )

        self.model = (
            model
            or os.getenv(
                "OPENROUTER_MODEL"
            )
        )

        if not self.model:
            raise ValueError(
                "OPENROUTER_MODEL is not configured."
            )

        self.temperature = (
            temperature
            if temperature is not None
            else float(
                os.getenv(
                    "OPENROUTER_TEMPERATURE",
                    "0.2",
                )
            )
        )

        self.max_tokens = (
            max_tokens
            if max_tokens is not None
            else int(
                os.getenv(
                    "OPENROUTER_MAX_TOKENS",
                    "1000",
                )
            )
        )

        self.client = OpenAI(
            api_key=self.api_key,
            base_url=self.base_url,
        )

    def generate(
        self,
        prompt: str,
    ) -> str:

        if not prompt.strip():
            raise ValueError(
                "Prompt cannot be empty."
            )

        response = self.client.chat.completions.create(
            model=self.model,
            messages=[
                {
                    "role": "user",
                    "content": prompt,
                }
            ],
            temperature=self.temperature,
            max_tokens=self.max_tokens,
        )

        content = (
            response.choices[0]
            .message
            .content
        )

        if not content:
            return ""

        return content.strip()