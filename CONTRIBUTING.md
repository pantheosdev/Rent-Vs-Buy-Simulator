# Contributing

Thanks for considering a contribution to the Rent vs. Buy Simulator!

## Getting Started

1. Clone the repo:
   ```bash
   git clone https://github.com/pantheosdev/Rent-Vs-Buy-Simulator.git
   cd Rent-Vs-Buy-Simulator
   ```
2. Create and activate a virtual environment:
   ```bash
   python -m venv .venv && source .venv/bin/activate
   ```
3. Install dependencies:
   ```bash
   pip install -r requirements.txt -r requirements-dev.txt
   ```
4. Verify everything works:
   ```bash
   streamlit run app.py
   ```

## Running Tests

- **Quick smoke test:**
  ```bash
  python -m pytest tests/test_smoke.py -v
  ```
- **Full QA suite:**
  ```bash
  python run_all_qa.py
  # or
  make qa
  ```
- **Full pytest suite:**
  ```bash
  python -m pytest tests/ -v --tb=short
  ```
- **With coverage:**
  ```bash
  python -m pytest tests/ -v --cov=rbv --cov-report=term-missing
  ```

## Pre-Push Checklist

Run preflight before pushing:
```bash
python scripts/preflight.py
# or
make preflight-fast
```
This runs `ruff format`, `ruff check`, and the full QA suite.

For visual regression testing (requires Playwright):
```bash
make preflight
```

## Lint & Type Checking

```bash
ruff check .
ruff format .
python -m mypy rbv/core/ --ignore-missing-imports
```

## Docker

```bash
docker build -t rbv-simulator . && docker run -p 8501:8501 rbv-simulator
# or
docker-compose up
```

## Pull Request Guidelines

- Branch from `main`.
- One focused change per PR.
- **CRITICAL:** Never do large-scale refactors of `app.py` or `engine.py` in a single PR (see PRs #44/#45 for why).
- All PRs must pass:
  ```bash
  python run_all_qa.py
  python -m pytest tests/
  ruff check .
  ```
- If touching the UI, run `make vr-smoke` and include before/after screenshots.
- Do **NOT** modify `app.py` unless specifically approved — it's the 342KB monolith being carefully decomposed.

## Project Structure

See [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md) for the full layout. Key directories:

| Path | Description |
|------|-------------|
| `app.py` | Streamlit UI orchestrator |
| `rbv/core/` | Financial engine, policy, taxes, mortgage helpers |
| `rbv/ui/` | Theme, charts, costs tab helpers |
| `rbv/qa/` | QA test modules |
| `tests/` | pytest wrappers |
| `tools/visual_regression/` | Playwright snapshot harness |
| `scripts/` | Preflight, release builder |
| `docs/` | Architecture, methodology, assumptions |

## Reporting Issues

- Include clear reproduction steps.
- Include the province/scenario config if it's a calculation bug.
- Attach screenshots for UI issues.
