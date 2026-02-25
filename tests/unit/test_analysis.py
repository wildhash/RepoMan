"""Unit tests for the analysis modules."""

from __future__ import annotations

from pathlib import Path

import pytest

from repoman.analysis.complexity import analyse_python_file, cyclomatic_complexity
from repoman.analysis.dependency import parse_dependencies
from repoman.analysis.health import compute_initial_health_score, compute_weighted_score
from repoman.analysis.language import detect_frameworks, detect_languages
from repoman.analysis.structure import build_file_tree, get_directory_structure
from repoman.core.state import RepoSnapshot


class TestLanguageDetection:
    """Tests for language detection."""

    def test_detects_python(self, tmp_path: Path) -> None:
        """Should detect Python from .py files."""
        (tmp_path / "main.py").write_text("print('hello')\n" * 10)
        langs = detect_languages(str(tmp_path))
        assert "Python" in langs
        assert langs["Python"] == pytest.approx(1.0, abs=0.01)

    def test_detects_multiple_languages(self, tmp_path: Path) -> None:
        """Should detect multiple languages proportionally."""
        (tmp_path / "app.py").write_text("x = 1\n" * 100)
        (tmp_path / "app.js").write_text("var x = 1;\n" * 100)
        langs = detect_languages(str(tmp_path))
        assert "Python" in langs
        assert "JavaScript" in langs

    def test_skips_skip_dirs(self, tmp_path: Path) -> None:
        """Should skip node_modules and __pycache__."""
        skip = tmp_path / "node_modules"
        skip.mkdir()
        (skip / "dep.js").write_text("var x = 1;\n" * 100)
        (tmp_path / "main.py").write_text("x = 1\n" * 10)
        langs = detect_languages(str(tmp_path))
        assert "JavaScript" not in langs

    def test_detects_react_framework(self, tmp_path: Path) -> None:
        """Should detect React from package.json."""
        (tmp_path / "package.json").write_text('{"dependencies": {"react": "^18.0.0"}}')
        frameworks = detect_frameworks(str(tmp_path))
        assert "React" in frameworks

    def test_detects_fastapi_framework(self, tmp_path: Path) -> None:
        """Should detect FastAPI from requirements.txt."""
        (tmp_path / "requirements.txt").write_text("fastapi==0.111.0\nuvicorn\n")
        frameworks = detect_frameworks(str(tmp_path))
        assert "FastAPI" in frameworks

    def test_detects_django_framework(self, tmp_path: Path) -> None:
        """Should detect Django from requirements.txt."""
        (tmp_path / "requirements.txt").write_text("Django>=4.0\n")
        frameworks = detect_frameworks(str(tmp_path))
        assert "Django" in frameworks


class TestDependencyParsing:
    """Tests for dependency parsing."""

    def test_parses_requirements_txt(self, tmp_path: Path) -> None:
        """Should parse Python requirements.txt."""
        (tmp_path / "requirements.txt").write_text("fastapi>=0.111.0\nuvicorn==0.29.0\n")
        deps = parse_dependencies(str(tmp_path))
        names = [d["name"] for d in deps]
        assert "fastapi" in names
        assert "uvicorn" in names

    def test_parses_package_json(self, tmp_path: Path) -> None:
        """Should parse Node.js package.json."""
        (tmp_path / "package.json").write_text(
            '{"dependencies": {"express": "^4.0.0"}, "devDependencies": {"jest": "^29.0.0"}}'
        )
        deps = parse_dependencies(str(tmp_path))
        names = [d["name"] for d in deps]
        assert "express" in names
        assert "jest" in names

    def test_dep_types(self, tmp_path: Path) -> None:
        """Should assign correct runtime/dev types."""
        (tmp_path / "package.json").write_text(
            '{"dependencies": {"react": "^18"}, "devDependencies": {"typescript": "^5"}}'
        )
        deps = parse_dependencies(str(tmp_path))
        types = {d["name"]: d["type"] for d in deps}
        assert types.get("react") == "runtime"
        assert types.get("typescript") == "dev"

    def test_empty_directory(self, tmp_path: Path) -> None:
        """Should return empty list for a repo with no manifest files."""
        deps = parse_dependencies(str(tmp_path))
        assert deps == []


class TestHealthScoring:
    """Tests for health score computation."""

    def test_base_score(self) -> None:
        """Minimal repo should have at least base score."""
        snapshot = RepoSnapshot(
            url="https://github.com/test/repo", name="repo", clone_path="/tmp/repo"
        )
        score = compute_initial_health_score(snapshot)
        assert score >= 30.0

    def test_full_repo_higher_score(self) -> None:
        """Repo with all hygiene indicators should score higher."""
        snapshot = RepoSnapshot(
            url="https://github.com/test/repo",
            name="repo",
            clone_path="/tmp/repo",
            has_readme=True,
            has_tests=True,
            has_ci=True,
            has_dockerfile=True,
            has_license=True,
            has_env_example=True,
            total_files=50,
        )
        score = compute_initial_health_score(snapshot)
        assert score >= 75.0

    def test_score_capped_at_100(self) -> None:
        """Score should never exceed 100."""
        snapshot = RepoSnapshot(
            url="https://github.com/test/repo",
            name="repo",
            clone_path="/tmp/repo",
            has_readme=True,
            has_tests=True,
            has_ci=True,
            has_dockerfile=True,
            has_license=True,
            has_env_example=True,
            total_files=50,
        )
        score = compute_initial_health_score(snapshot)
        assert score <= 100.0

    def test_weighted_score(self) -> None:
        """Weighted score should compute correctly."""
        dims = {k: 8.0 for k in ["architecture", "code_quality", "test_coverage", "security",
                                   "documentation", "performance", "maintainability", "deployment_readiness"]}
        score = compute_weighted_score(dims)
        assert score == pytest.approx(8.0, abs=0.01)

    def test_weighted_score_missing_dims(self) -> None:
        """Missing dimensions should default to 5.0."""
        score = compute_weighted_score({"architecture": 10.0})
        assert 0.0 < score <= 10.0


class TestComplexityAnalysis:
    """Tests for code complexity analysis."""

    def test_simple_function_complexity(self) -> None:
        """Simple function should have low complexity."""
        source = "def foo():\n    return 42\n"
        assert cyclomatic_complexity(source) == 1

    def test_branching_increases_complexity(self) -> None:
        """If/for/while should increase complexity."""
        source = """
def foo(x):
    if x > 0:
        for i in range(x):
            while i > 0:
                i -= 1
    return x
"""
        assert cyclomatic_complexity(source) > 1

    def test_invalid_syntax_returns_one(self) -> None:
        """Invalid Python syntax should return complexity of 1."""
        assert cyclomatic_complexity("this is not python!!!") == 1

    def test_analyse_python_file(self, tmp_path: Path) -> None:
        """Should return metrics for a Python file."""
        f = tmp_path / "sample.py"
        f.write_text("def foo():\n    pass\n\nclass Bar:\n    pass\n")
        result = analyse_python_file(str(f))
        assert result["functions"] == 1
        assert result["classes"] == 1
        assert result["lines"] >= 4


class TestStructureAnalysis:
    """Tests for file tree structure analysis."""

    def test_build_file_tree(self, tmp_path: Path) -> None:
        """Should return relative paths of all files."""
        (tmp_path / "a.py").write_text("x")
        sub = tmp_path / "sub"
        sub.mkdir()
        (sub / "b.py").write_text("x")
        tree = build_file_tree(str(tmp_path))
        assert "a.py" in tree
        assert "sub/b.py" in tree

    def test_skips_skip_dirs(self, tmp_path: Path) -> None:
        """Should not include files from skipped directories."""
        skip = tmp_path / "__pycache__"
        skip.mkdir()
        (skip / "cache.pyc").write_text("x")
        (tmp_path / "main.py").write_text("x")
        tree = build_file_tree(str(tmp_path))
        assert "main.py" in tree
        assert not any("__pycache__" in p for p in tree)

    def test_directory_structure(self) -> None:
        """Should build nested dict from file tree."""
        tree = ["src/main.py", "src/utils/helper.py", "README.md"]
        structure = get_directory_structure(tree)
        assert "src" in structure
        assert "main.py" in structure["src"]
        assert "README.md" in structure
