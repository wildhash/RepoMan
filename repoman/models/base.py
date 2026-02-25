"""Abstract LLM provider interface."""

from __future__ import annotations

from abc import ABC, abstractmethod

from pydantic import BaseModel


class Message(BaseModel):
    """A single LLM conversation message."""

    role: str  # user | assistant | system
    content: str


class LLMResponse(BaseModel):
    """Response from an LLM provider."""

    content: str
    model: str
    input_tokens: int = 0
    output_tokens: int = 0


class BaseLLMProvider(ABC):
    """Abstract base for all LLM provider implementations."""

    @abstractmethod
    async def complete(
        self,
        messages: list[Message],
        system_prompt: str = "",
        temperature: float = 0.3,
        max_tokens: int = 8192,
    ) -> LLMResponse:
        """Send messages and return the model response.

        Args:
            messages: Conversation history.
            system_prompt: Optional system-level instruction.
            temperature: Sampling temperature.
            max_tokens: Maximum tokens in the response.

        Returns:
            LLMResponse with content and usage stats.
        """

    async def complete_json(
        self,
        messages: list[Message],
        system_prompt: str = "",
        temperature: float = 0.3,
        max_tokens: int = 8192,
    ) -> LLMResponse:
        """Like complete() but appends a JSON-only instruction to the system prompt.

        Args:
            messages: Conversation history.
            system_prompt: Optional system-level instruction.
            temperature: Sampling temperature.
            max_tokens: Maximum tokens in the response.

        Returns:
            LLMResponse guaranteed to contain only JSON content.
        """
        json_prompt = (system_prompt + "\nRespond with valid JSON only.").strip()
        return await self.complete(messages, json_prompt, temperature, max_tokens)
