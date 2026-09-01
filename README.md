# normfix

A safe, extensible CLI for detecting and automatically fixing mechanical [42 School](https://www.42.fr/) Norm violations in C projects.

## Status

Early development. The fixer pipeline now handles mechanical formatting while deliberately leaving semantic refactors and existing 42 headers alone.

## Design principles

- Dry-run by default.
- Fixers produce edits; they never write files directly.
- Diagnostics are independent from the CLI.
- Rules are registered through a single extension point.
- Source transformations must be deterministic and idempotent.
- Changes are verified with Norminette after application.
- Semantic refactors are never performed by formatting fixers.
- **42 headers are immutable.** normfix never creates, replaces, updates, or reformats them.
- Existing includes and source text outside the actual fix target must be preserved.

## Currently supported mechanical fixes

- Indentation and tabs
- Function return-type spacing
- Brace placement
- Consecutive spaces
- Declaration/assignment separation
- Variable declaration alignment
- Required blank line after local declarations
- Empty-line cleanup inside functions
- Preprocessor spacing
- Trailing whitespace

Structural rules such as function length, function count, parameter count, and forbidden control structures remain report-only.

## Commands

```text
normfix check <path>
normfix fix <path>
normfix explain <RULE_CODE>
```

## Development

```bash
python -m pip install -e .
pytest
```
