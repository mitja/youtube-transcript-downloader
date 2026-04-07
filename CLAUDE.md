# CLAUDE.md

## Project

Python package for downloading YouTube transcripts. Uses `uv` as the package manager.

## Commands

- `make` — install, lint, and test (default target)
- `make build` — build sdist and wheel
- `make clean` — remove build artifacts and caches
- `uv run pytest` — run tests only
- `uv run python devtools/lint.py` — run linting only (ruff, basedpyright, codespell)

## Development Workflow

1. **Create a feature branch** before making any changes: `git checkout -b feature/<name>`.
2. Implement the changes.
3. Run `make` and fix any lint errors or test failures until it passes cleanly.
4. Make granular commits — one commit per logical task.
5. Create a pull request. Include test results (number of tests passed, any skipped) and a summary of fixes performed in the PR description.
