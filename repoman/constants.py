"""RepoMan constants."""

SKIP_DIRS = {".git", "node_modules", "__pycache__", "venv", ".venv", "dist", "build", ".tox"}

EXTENSION_TO_LANGUAGE = {
    ".py": "Python",
    ".js": "JavaScript",
    ".jsx": "JavaScript",
    ".ts": "TypeScript",
    ".tsx": "TypeScript",
    ".rs": "Rust",
    ".go": "Go",
    ".java": "Java",
    ".cpp": "C++",
    ".cc": "C++",
    ".cxx": "C++",
    ".rb": "Ruby",
    ".php": "PHP",
}

EXECUTION_ORDER = [
    "fix_critical_bugs",
    "fix_security_vulnerabilities",
    "restructure_files",
    "update_dependencies",
    "refactor_code",
    "add_error_handling",
    "add_type_hints",
    "write_tests",
    "generate_documentation",
    "setup_cicd",
    "setup_docker",
    "add_env_management",
    "final_lint_format",
]

HEALTH_WEIGHTS = {
    "architecture": 0.15,
    "code_quality": 0.15,
    "test_coverage": 0.15,
    "security": 0.15,
    "documentation": 0.10,
    "performance": 0.10,
    "maintainability": 0.10,
    "deployment_readiness": 0.10,
}
