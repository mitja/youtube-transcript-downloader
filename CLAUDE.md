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

- Work in feature branches, not directly on `main`.
- Make commits granular — one commit per logical task.
- Before committing, run `make` and fix any lint errors or test failures.
- After each phase of work, create a pull request. Include details about test results and any fixes performed in the PR description.
