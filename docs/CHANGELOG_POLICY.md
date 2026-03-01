# Changelog Policy

## Version Numbering

The project uses semantic-ish versioning: `vMAJOR.MINOR.PATCH`

- **MAJOR** (`v3.x`): Reserved for breaking changes to the engine API or config format (e.g., if `run_simulation_core()` signature changes)
- **MINOR** (`v2.94.x`): New features, new policy implementations (e.g., adding FHSA support), significant UI additions
- **PATCH** (`v2.93.x`): Bug fixes, documentation updates, CI/tooling improvements, hygiene cleanup

## When to Bump

- Every PR that merges to `main` should add a CHANGELOG entry
- Group related PRs under one version bump when they are merged in quick succession
- The version in `rbv/__init__.py` must always match the latest entry in `CHANGELOG.md`

## CHANGELOG Format

```markdown
## vX.Y.Z — YYYY-MM-DD
### Added
- New feature description

### Changed
- Changed behavior description

### Fixed
- Bug fix description

### Removed
- Removed feature description
```

## Rules

- Versions in `CHANGELOG.md` must be in strictly descending order (newest first)
- Never duplicate a version number
- Always include the date
- Use the categories: `Added`, `Changed`, `Fixed`, `Removed` (per [Keep a Changelog](https://keepachangelog.com/) convention)
- Reference the PR number where applicable: `(#55)`

## Automation

- The `scripts/preflight.py` script checks for version consistency
- CI will eventually enforce that `rbv/__init__.py` version matches the top CHANGELOG entry
