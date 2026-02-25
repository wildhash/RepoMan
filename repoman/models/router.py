"""Model router with fallback support."""

from __future__ import annotations

import structlog

from repoman.config import Settings
from repoman.models.anthropic_provider import AnthropicProvider
from repoman.models.base import BaseLLMProvider, LLMResponse, Message
from repoman.models.openai_provider import OpenAIProvider

log = structlog.get_logger()


class ModelRouter:
    """Routes agent requests to the appropriate LLM provider with fallback."""

    def __init__(self, config: Settings) -> None:
        """Initialise providers from config.

        Args:
            config: Application settings.
        """
        self._config = config
        self._providers: dict[str, BaseLLMProvider] = {}
        self._fallback_chain: list[BaseLLMProvider] = []
        self._setup_providers()

    def _setup_providers(self) -> None:
        """Construct provider instances for each agent role."""
        cfg = self._config
        if cfg.anthropic_api_key:
            self._providers["orchestrator"] = AnthropicProvider(cfg.anthropic_api_key, cfg.orchestrator_model)
            self._providers["architect"] = AnthropicProvider(cfg.anthropic_api_key, cfg.architect_model)
            self._providers["builder"] = AnthropicProvider(cfg.anthropic_api_key, cfg.builder_model)
            self._fallback_chain.append(
                AnthropicProvider(cfg.anthropic_api_key, cfg.orchestrator_model)
            )
        if cfg.openai_api_key:
            self._providers["auditor"] = OpenAIProvider(cfg.openai_api_key, cfg.auditor_model)
            self._fallback_chain.append(OpenAIProvider(cfg.openai_api_key, cfg.auditor_model))

    async def complete(
        self,
        role: str,
        messages: list[Message],
        system_prompt: str = "",
        **kwargs,
    ) -> LLMResponse:
        """Complete a request for the given agent role.

        Tries the primary provider for the role, then falls through to the
        fallback chain on any exception.

        Args:
            role: Agent role name used to select the provider.
            messages: Conversation history.
            system_prompt: System instruction.
            **kwargs: Additional arguments forwarded to the provider.

        Returns:
            LLMResponse from the first successful provider.

        Raises:
            RuntimeError: If no provider succeeds.
        """
        providers_to_try: list[BaseLLMProvider] = []
        if role in self._providers:
            providers_to_try.append(self._providers[role])
        providers_to_try.extend(
            p for p in self._fallback_chain if p not in providers_to_try
        )

        last_exc: Exception | None = None
        for provider in providers_to_try:
            try:
                response = await provider.complete(messages, system_prompt, **kwargs)
                await log.ainfo("llm_call", role=role, model=response.model,
                                input_tokens=response.input_tokens,
                                output_tokens=response.output_tokens)
                return response
            except Exception as exc:
                log.warning("provider_fallback", role=role, error=str(exc))
                last_exc = exc

        raise RuntimeError(f"All providers failed for role '{role}'") from last_exc

    async def complete_json(
        self,
        role: str,
        messages: list[Message],
        system_prompt: str = "",
        **kwargs,
    ) -> LLMResponse:
        """Like complete() but appends JSON-only instruction.

        Args:
            role: Agent role name.
            messages: Conversation history.
            system_prompt: System instruction.
            **kwargs: Additional arguments forwarded to the provider.

        Returns:
            LLMResponse with JSON content.
        """
        json_prompt = (system_prompt + "\nRespond with valid JSON only.").strip()
        return await self.complete(role, messages, json_prompt, **kwargs)
