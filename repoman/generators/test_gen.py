"""Test generation using LLM."""

from __future__ import annotations

from repoman.models.router import ModelRouter


class TestGenerator:
    """Generates unit and integration tests using an LLM."""

    def __init__(self, router: ModelRouter) -> None:
        """Initialise the test generator.

        Args:
            router: Model router instance.
        """
        self._router = router

    async def generate_tests(self, source_code: str, language: str, file_path: str) -> str:
        """Generate tests for the given source code.

        Args:
            source_code: Source code to write tests for.
            language: Programming language.
            file_path: Source file path (for naming conventions).

        Returns:
            Generated test file content.
        """
        from repoman.models.base import Message

        prompt = f"""Generate comprehensive tests for this {language} code.

File: {file_path}

Source:
```{language.lower()}
{source_code[:3000]}
```

Write unit tests covering: happy paths, edge cases, and error conditions.
Return only the test file content."""

        messages = [Message(role="user", content=prompt)]
        response = await self._router.complete("builder", messages)
        return response.content
