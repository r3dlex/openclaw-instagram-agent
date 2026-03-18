# Pipelines

All quality gates are implemented as Python pipelines in `tools/pipeline_runner/`. Pipelines are composable sequences of steps that enforce [ADRs](.archgate/adrs/) and project standards.

## Running Pipelines

```bash
# Via Poetry
poetry run pipeline ci          # Full CI pipeline
poetry run pipeline test        # Lint + tests only
poetry run pipeline security    # Secret scan + env checks
poetry run pipeline docs        # ADR + docs integrity
poetry run pipeline pre-commit  # Fast pre-commit checks

# List available pipelines
poetry run pipeline --list

# JSON output (for CI integration)
poetry run pipeline ci --json

# Via Docker
docker compose run --rm --entrypoint pipeline agent ci
```

## Available Pipelines

### `ci` — Full CI Pipeline

The master gate. Runs all checks before merge.

| Step | What it does | Enforces |
|------|-------------|----------|
| `lint` | ruff check on src/, tests/, tools/ | Code quality |
| `unit-tests` | pytest tests/ | ARCH-001, ARCH-002, ARCH-005 |
| `env-check` | .env.example exists, .env gitignored | ARCH-003 |
| `secret-scan` | Regex scan for hardcoded secrets | ARCH-003 |
| `adr-compliance` | ADR files have valid structure | ARCH-005 |
| `docs-integrity` | All required spec/ docs exist | ARCH-005 |

### `test` — Test Pipeline

Fast feedback during development.

| Step | What it does |
|------|-------------|
| `lint` | ruff check |
| `unit-tests` | pytest tests/ |

### `security` — Security Pipeline

Run before any commit touching config or credentials.

| Step | What it does | Enforces |
|------|-------------|----------|
| `env-check` | .env.example exists | ARCH-003 |
| `secret-scan` | Hardcoded secret patterns | ARCH-003 |
| `gitignore-check` | .env not in git cache | ARCH-003 |

### `docs` — Documentation Pipeline

Validates architectural governance.

| Step | What it does | Enforces |
|------|-------------|----------|
| `adr-compliance` | ADR frontmatter + structure | ARCH-005 |
| `docs-integrity` | Required docs exist in spec/ | ARCH-005 |

### `pre-commit` — Pre-Commit Pipeline

Minimal checks for fast commit cycles.

| Step | What it does |
|------|-------------|
| `lint` | ruff check |
| `secret-scan` | Hardcoded secrets |
| `env-check` | .env.example exists |

## ADR ↔ Pipeline Mapping

Every ADR specifies which pipeline enforces it in its `enforced_by` frontmatter field.

| ADR | Decision | Enforced by |
|-----|----------|-------------|
| ARCH-001 | API-first, browser fallback | `ci` (unit-tests) |
| ARCH-002 | Human-like rate limiting | `ci` (unit-tests) |
| ARCH-003 | Env-only configuration | `security` |
| ARCH-004 | Zero-install execution | `ci` |
| ARCH-005 | Pipeline-assured quality | `ci`, `docs` |
| ARCH-006 | Human approval for text | `ci` (code review) |

## Writing New Steps

Steps are factory functions in `tools/pipeline_runner/steps.py`:

```python
from tools.pipeline_runner.engine import StepResult, StepStatus

def my_check():
    """Factory: returns a step callable."""
    def _step() -> StepResult:
        # ... your check logic ...
        return StepResult(
            name="my_check",
            status=StepStatus.PASSED,  # or FAILED
            message="",  # error details if failed
        )
    return _step
```

Register in a pipeline in `tools/pipeline_runner/pipelines.py`:

```python
p.add_step(Step("my-check", my_check()))
```

## GitHub Actions

Pipelines run automatically on every push and PR via `.github/workflows/ci.yml`. Three parallel jobs map directly to pipeline commands:

| Job | Pipeline | Trigger |
|-----|----------|---------|
| `ci` | `poetry run pipeline ci` | push to main, PRs |
| `security` | `poetry run pipeline security` | push to main, PRs |
| `docs` | `poetry run pipeline docs` | push to main, PRs |

The CI workflow:
1. Checks out the repo
2. Sets up Python 3.11 + Poetry with dependency caching
3. Copies `.env.example` to `.env` (dummy values, no real secrets)
4. Runs the pipeline with `--json` output for structured CI logs

No secrets are needed in GitHub Actions — all pipelines run with the dummy `.env.example` values. Instagram credentials are never required for CI.

## Testing Pipelines

Pipeline engine and steps are tested in `tests/test_pipeline.py`. See `spec/TESTING.md` for how to run tests.
