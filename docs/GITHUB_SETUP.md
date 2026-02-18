# GitHub setup checklist

## Branch protection (recommended)
GitHub → **Settings → Branches → Add branch protection rule**

- Branch name pattern: `main`
- ✅ Require a pull request before merging
- ✅ Require status checks to pass before merging
  - Select: **QA** and **Lint (Ruff)** (and **Visual Regression (PR)** once baselines exist)
- ✅ Require branches to be up to date before merging
- ✅ Block force pushes

## Dependabot PRs
Dependabot PR checks can fail if the PR branch is behind `main`.
On the PR page, click **Update branch** to rebase onto the latest `main`, then re-run checks.

## Visual regression baselines
Generate baselines on a Linux environment (WSL2 recommended on Windows) for best CI consistency:

```bash
pip install -r requirements.txt -r requirements-dev.txt
python -m playwright install --with-deps chromium
make vr-update
```

Commit the baseline PNGs under `tools/visual_regression/baseline/`.
