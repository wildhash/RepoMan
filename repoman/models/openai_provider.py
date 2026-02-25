"""OpenAI (GPT) LLM provider."""

from __future__ import annotations

import openai

from repoman.models.base import BaseLLMProvider, LLMResponse, Message


class OpenAIProvider(BaseLLMProvider):
    """Wraps the OpenAI async client for GPT models."""

    def __init__(self, api_key: str, model: str) -> None:
        """Initialise the provider.

        Args:
            api_key: OpenAI API key.
            model: GPT model identifier.
        """
        self._client = openai.AsyncOpenAI(api_key=api_key)
        self._model = model

    async def complete(
        self,
        messages: list[Message],
        system_prompt: str = "",
        temperature: float = 0.3,
        max_tokens: int = 8192,
    ) -> LLMResponse:
        """Send messages to GPT and return the response.

        Args:
            messages: Conversation history.
            system_prompt: System-level instruction prepended to messages.
            temperature: Sampling temperature.
            max_tokens: Maximum tokens in the completion.

        Returns:
            LLMResponse with content and token usage.
        """
        oai_messages: list[dict] = []
        if system_prompt:
            oai_messages.append({"role": "system", "content": system_prompt})
        for m in messages:
            oai_messages.append({"role": m.role, "content": m.content})

        response = await self._client.chat.completions.create(
            model=self._model,
            messages=oai_messages,  # type: ignore[arg-type]
            temperature=temperature,
            max_tokens=max_tokens,
        )
        content = response.choices[0].message.content or ""
        usage = response.usage
        return LLMResponse(
            content=content,
            model=self._model,
            input_tokens=usage.prompt_tokens if usage else 0,
            output_tokens=usage.completion_tokens if usage else 0,
        )
