from __future__ import annotations

from pathlib import Path


def write(root: Path, rel: str, content: str = "x\n") -> Path:
    p = root / rel
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(content, encoding="utf-8")
    return p


def make_good_repo(root: Path) -> Path:
    write(root, "README.md", "# Proj\n\n## Installation\n\n## Usage\n\n## License\nMIT\n")
    write(root, "LICENSE", "MIT License\n")
    write(root, "CONTRIBUTING.md", "# Contributing\n")
    write(root, ".gitignore", "__pycache__/\n")
    write(root, "CODEOWNERS", "* @team\n")
    write(root, "pyproject.toml", "[project]\nname='p'\n[tool.coverage.run]\nsource=['p']\n")
    write(root, "poetry.lock", "# lock\n")
    write(root, "src/p/__init__.py", "")
    write(root, "src/p/core.py", "def add(a, b):\n    return a + b\n")
    write(root, "tests/test_core.py", "def test_add():\n    assert True\n")
    write(root, "docs/index.md", "# Docs\n")
    write(root, ".github/workflows/ci.yml",
          "jobs:\n  t:\n    steps:\n      - run: pytest\n      - uses: actions/checkout@v4\n      - run: echo cache\n")
    return root
