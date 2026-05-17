# Contributing

Thank you for helping improve **matryca-logseq-llm-wiki**. This project bridges AI agents with **Logseq OG** using pure local Markdown and a block-oriented outliner model.

## Workflow

1. **Fork** the repository and create a branch for your change.
2. **Open an issue** (or comment on an existing one) for larger features so design and scope stay aligned.
3. **Keep pull requests focused**: one logical change per PR is easier to review and bisect.

## Local setup

1. Use **Python 3.11+** (see ``.python-version``).
2. Install **[uv](https://docs.astral.sh/uv/)** if you do not have it yet.
3. Create the virtual environment and install the project with dev tools:

   ```bash
   uv venv --python 3.11
   uv sync --extra dev
   ```

   Activate when you need a classic shell:

   ```bash
   source .venv/bin/activate   # Windows: .venv\Scripts\activate
   ```

   Or run commands without activating:

   ```bash
   uv run ruff check .
   uv run mypy src/
   uv run pytest
   ```

4. Copy environment template and fill in values:

   ```bash
   cp .env.example .env
   ```

   Set `LOGSEQ_API_TOKEN`, `LOGSEQ_API_URL`, and `LOGSEQ_GRAPH_PATH` for your machine.

5. Quality checks (same as CI): ``uv run ruff check .``, ``uv run mypy src/``, ``uv run pytest``.

## The “atomic block” paradigm

Logseq OG treats **indented bullets** as a tree of blocks. When agents (or humans) edit files:

- Prefer **nested bullets** over flattening ideas into prose paragraphs.
- Preserve **`id:: <uuid>`** lines when moving or refactoring blocks so graph references stay stable.
- Assume **human–AI co-editing** on the same `.md` files; avoid changes that only make sense inside a proprietary database.

Code and tooling in this repo should reinforce block-grained read/write paths and clear validation at boundaries (e.g. Pydantic models for tool inputs).

## Pull request checklist

- Explain **why** the change is needed and any trade-offs.
- Keep types and docstrings accurate for public APIs.
- Do not commit secrets (no `.env`, tokens, or private graph paths).

## Code of conduct

Be respectful and constructive. Report problems privately if needed; we aim for a welcoming environment for contributors of all backgrounds.
