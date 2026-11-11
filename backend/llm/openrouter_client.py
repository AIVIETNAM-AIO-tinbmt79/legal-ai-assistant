from openai import OpenAI

from config.settings import settings


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

        # ==========================================
        # API Key
        # ==========================================

        self.api_key = (
            api_key
            if api_key is not None
            else settings.OPENROUTER_API_KEY
        )

        if not self.api_key:

            raise ValueError(
                "OPENROUTER_API_KEY is not configured."
            )


        # ==========================================
        # Base URL
        # ==========================================

        self.base_url = (
            settings.OPENROUTER_BASE_URL
        )


        # ==========================================
        # Model
        # ==========================================

        self.model = (
            model
            if model is not None
            else settings.OPENROUTER_MODEL
        )

        if not self.model:

            raise ValueError(
                "OPENROUTER_MODEL is not configured."
            )


        # ==========================================
        # Generation Config
        # ==========================================

        self.temperature = (
            temperature
            if temperature is not None
            else settings.OPENROUTER_TEMPERATURE
        )

        self.max_tokens = (
            max_tokens
            if max_tokens is not None
            else settings.OPENROUTER_MAX_TOKENS
        )


        # ==========================================
        # OpenAI Client
        # ==========================================

        self.client = OpenAI(
            api_key=self.api_key,
            base_url=self.base_url,
        )


    # ==================================================
    # Generate
    # ==================================================

    def generate(
        self,
        prompt: str,
    ) -> str:

        if not prompt or not prompt.strip():

            raise ValueError(
                "Prompt cannot be empty."
            )


        response = (
            self.client
            .chat
            .completions
            .create(
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
        )


        content = (
            response
            .choices[0]
            .message
            .content
        )


        if not content:

            return ""


        return content.strip()