"""Anthropic (Claude) LLM provider."""

from __future__ import annotations

import anthropic

from repoman.models.base import BaseLLMProvider, LLMResponse, Message


class AnthropicProvider(BaseLLMProvider):
    """Wraps the Anthropic async client for Claude models."""

    def __init__(self, api_key: str, model: str) -> None:
        """Initialise the provider.

        Args:
            api_key: Anthropic API key.
            model: Claude model identifier.
        """
        self._client = anthropic.AsyncAnthropic(api_key=api_key)
        self._model = model

    async def complete(
        self,
        messages: list[Message],
        system_prompt: str = "",
        temperature: float = 0.3,
        max_tokens: int = 8192,
    ) -> LLMResponse:
        """Send messages to Claude and return the response.

        Args:
            messages: Conversation history (user/assistant roles only).
            system_prompt: Claude system prompt.
            temperature: Sampling temperature.
            max_tokens: Maximum tokens in the completion.

        Returns:
            LLMResponse with content and token usage.
        """
        anthropic_messages = [
            {"role": m.role, "content": m.content}
            for m in messages
            if m.role in ("user", "assistant")
        ]
        kwargs: dict = {
            "model": self._model,
            "max_tokens": max_tokens,
            "temperature": temperature,
            "messages": anthropic_messages,
        }
        if system_prompt:
            kwargs["system"] = system_prompt

        response = await self._client.messages.create(**kwargs)
        content = response.content[0].text if response.content else ""
        return LLMResponse(
            content=content,
            model=self._model,
            input_tokens=response.usage.input_tokens,
            output_tokens=response.usage.output_tokens,
        )
