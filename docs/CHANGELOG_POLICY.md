# Changelog Policy

## Version Numbering

The project uses semantic-ish versioning: `vMAJOR.MINOR.PATCH`

| Segment | When to bump |
|---------|-------------|
| **MAJOR** | Breaking changes to the engine API or simulation output format |
| **MINOR** | New features, new provinces/policies, significant UI changes |
| **PATCH** | Bug fixes, doc updates, QA improvements, hygiene |

## Current Version

The canonical version is stored in `rbv/__init__.py` as `__version__`:

```python
__version__ = "vX.Y.Z"
```

This value **MUST** match the latest entry in `CHANGELOG.md`. Both must be updated in the same PR.

## CHANGELOG Format

- **File:** `CHANGELOG.md` in the repository root
- **Order:** Entries are ordered **strictly descending** (newest first)
- **Entry format:**

```
## vX.Y.Z — YYYY-MM-DD
### Added / Changed / Fixed / Removed
- Description of change (reference PR # if applicable)
```

Example:

```
## v2.94.0 — 2026-03-15
### Added
- Province selector now supports Nova Scotia transfer tax rules (PR #52)
### Fixed
- Corrected amortization edge case for insured 30-year loans (PR #51)
```

## When to Update

| PR type | CHANGELOG entry |
|---------|----------------|
| Changes functionality (engine, UI, policy, QA) | **MUST** add an entry |
| Documentation-only or CI-only | **MAY** add an entry (recommended for significant changes) |

The version in `rbv/__init__.py` **MUST** be bumped in the same PR as the CHANGELOG entry.

## Anti-patterns (learned the hard way)

- **Do NOT** have duplicate version entries (Bug B6 from audit)
- **Do NOT** have entries out of chronological order (newest must be at the top)
- **Do NOT** forget to update `rbv/__init__.py` when adding a new version entry
