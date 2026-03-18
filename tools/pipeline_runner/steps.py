"""Reusable pipeline step factories.

Each factory returns a callable suitable for use as a Pipeline step function.
These provide the building blocks for composing pipelines.
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

from tools.pipeline_runner.engine import StepResult, StepStatus

PROJECT_ROOT = Path(__file__).resolve().parents[2]


def shell(cmd: str, cwd: Path | None = None) -> StepResult:
    """Run a shell command and return a StepResult."""
    proc = subprocess.run(
        cmd,
        shell=True,
        cwd=cwd or PROJECT_ROOT,
        capture_output=True,
        text=True,
        timeout=300,
    )
    status = StepStatus.PASSED if proc.returncode == 0 else StepStatus.FAILED
    return StepResult(
        name=cmd,
        status=status,
        message=proc.stderr.strip() if proc.returncode != 0 else "",
        details={
            "stdout": proc.stdout.strip(),
            "stderr": proc.stderr.strip(),
            "returncode": proc.returncode,
        },
    )


def run_shell(cmd: str, cwd: Path | None = None):
    """Factory: returns a step fn that runs a shell command."""

    def _step() -> StepResult:
        return shell(cmd, cwd)

    return _step


def run_pytest(path: str = "tests/", *args: str):
    """Factory: returns a step fn that runs pytest on a path."""

    def _step() -> StepResult:
        cmd = [sys.executable, "-m", "pytest", path, "-v", *args]
        proc = subprocess.run(
            cmd,
            cwd=PROJECT_ROOT,
            capture_output=True,
            text=True,
            timeout=300,
        )
        status = StepStatus.PASSED if proc.returncode == 0 else StepStatus.FAILED
        return StepResult(
            name=f"pytest {path}",
            status=status,
            message=proc.stderr.strip() if proc.returncode != 0 else "",
            details={"stdout": proc.stdout.strip(), "returncode": proc.returncode},
        )

    return _step


def run_ruff(paths: list[str] | None = None):
    """Factory: returns a step fn that runs ruff linter."""
    targets = paths or ["src/", "tests/", "tools/"]

    def _step() -> StepResult:
        cmd = [sys.executable, "-m", "ruff", "check", *targets]
        proc = subprocess.run(
            cmd,
            cwd=PROJECT_ROOT,
            capture_output=True,
            text=True,
            timeout=120,
        )
        status = StepStatus.PASSED if proc.returncode == 0 else StepStatus.FAILED
        return StepResult(
            name="ruff check",
            status=status,
            message=proc.stdout.strip() if proc.returncode != 0 else "",
            details={"stdout": proc.stdout.strip(), "returncode": proc.returncode},
        )

    return _step


def check_env_example():
    """Step fn: verify .env.example exists and .env is gitignored."""

    def _step() -> StepResult:
        env_example = PROJECT_ROOT / ".env.example"
        gitignore = PROJECT_ROOT / ".gitignore"

        issues: list[str] = []
        if not env_example.exists():
            issues.append(".env.example not found")

        if gitignore.exists():
            content = gitignore.read_text()
            if ".env" not in content:
                issues.append(".env not in .gitignore")
        else:
            issues.append(".gitignore not found")

        if issues:
            return StepResult(
                name="check_env_example",
                status=StepStatus.FAILED,
                message="; ".join(issues),
            )
        return StepResult(name="check_env_example", status=StepStatus.PASSED)

    return _step


def check_no_secrets(patterns: list[str] | None = None):
    """Step fn: scan tracked files for secret patterns."""

    def _step() -> StepResult:
        default_patterns = [
            r"password\s*=\s*['\"][^'\"]+['\"]",
            r"secret\s*=\s*['\"][^'\"]+['\"]",
            r"token\s*=\s*['\"][^'\"]+['\"]",
            r"FYEO",
        ]
        search_patterns = patterns or default_patterns

        cmd = "git ls-files -- '*.py' '*.md' '*.yml' '*.toml' '*.sh'"
        proc = subprocess.run(
            cmd, shell=True, cwd=PROJECT_ROOT, capture_output=True, text=True
        )
        files = [f for f in proc.stdout.strip().split("\n") if f]

        violations: list[str] = []
        import re

        for filepath in files:
            full = PROJECT_ROOT / filepath
            if not full.exists():
                continue
            try:
                content = full.read_text()
            except Exception:
                continue
            for pat in search_patterns:
                matches = re.findall(pat, content, re.IGNORECASE)
                if matches:
                    violations.append(f"{filepath}: matched pattern '{pat}'")

        if violations:
            return StepResult(
                name="check_no_secrets",
                status=StepStatus.FAILED,
                message=f"{len(violations)} potential secret(s) found",
                details={"violations": violations},
            )
        return StepResult(name="check_no_secrets", status=StepStatus.PASSED)

    return _step


def check_adrs():
    """Step fn: verify ADR files exist and have valid frontmatter."""

    def _step() -> StepResult:
        adr_dir = PROJECT_ROOT / ".archgate" / "adrs"
        if not adr_dir.exists():
            return StepResult(
                name="check_adrs",
                status=StepStatus.FAILED,
                message=".archgate/adrs/ directory not found",
            )

        adrs = sorted(adr_dir.glob("ARCH-*.md"))
        if not adrs:
            return StepResult(
                name="check_adrs",
                status=StepStatus.FAILED,
                message="No ADR files found",
            )

        issues: list[str] = []
        for adr in adrs:
            content = adr.read_text()
            if not content.startswith("---"):
                issues.append(f"{adr.name}: missing YAML frontmatter")
            if "## Status" not in content:
                issues.append(f"{adr.name}: missing ## Status section")
            if "## Decision" not in content:
                issues.append(f"{adr.name}: missing ## Decision section")

        if issues:
            return StepResult(
                name="check_adrs",
                status=StepStatus.FAILED,
                message="; ".join(issues),
                details={"adr_count": len(adrs), "issues": issues},
            )
        return StepResult(
            name="check_adrs",
            status=StepStatus.PASSED,
            details={"adr_count": len(adrs)},
        )

    return _step


def check_docs_references():
    """Step fn: verify spec/ docs exist and key cross-references resolve."""

    def _step() -> StepResult:
        required_docs = [
            "spec/ARCHITECTURE.md",
            "spec/PIPELINES.md",
            "spec/TROUBLESHOOTING.md",
            "spec/TESTING.md",
            "spec/LEARNINGS.md",
        ]
        missing = [d for d in required_docs if not (PROJECT_ROOT / d).exists()]

        if missing:
            return StepResult(
                name="check_docs_references",
                status=StepStatus.FAILED,
                message=f"Missing docs: {', '.join(missing)}",
            )
        return StepResult(name="check_docs_references", status=StepStatus.PASSED)

    return _step
