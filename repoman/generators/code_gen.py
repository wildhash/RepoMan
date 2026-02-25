"""LLM-powered code generation."""

from __future__ import annotations

import structlog

from repoman.models.router import ModelRouter

log = structlog.get_logger()


class CodeGenerator:
    """Generates code using an LLM provider."""

    def __init__(self, router: ModelRouter) -> None:
        """Initialise the code generator.

        Args:
            router: Model router instance.
        """
        self._router = router

    async def generate(
        self, description: str, language: str, context: str = ""
    ) -> str:
        """Generate code for a given description.

        Args:
            description: What the code should do.
            language: Target programming language.
            context: Optional additional context.

        Returns:
            Generated code as a string.
        """
        from repoman.models.base import Message

        prompt = f"""Generate {language} code for the following:

{description}

{f"Context:{chr(10)}{context}" if context else ""}

Return only the code, no explanations. Code must be production quality with type hints and docstrings."""

        messages = [Message(role="user", content=prompt)]
        response = await self._router.complete("builder", messages)
        return response.content
