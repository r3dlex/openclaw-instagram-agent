"""Contract tests for the CI workflow and the uv composite action.

A security review of the mac-arm64 self-hosted probe found that the workflow
ran untrusted fork pull-request code on a persistent runner whose ``$HOME`` is
the operator's real home (GitHub OAuth token, SSH keys, Docker credentials),
and that the composite action depended on an ambient, unpinned ``uv`` that the
workflow never installed.

These tests pin the invariants that close those findings. The workflow and the
action are asserted textually: PyYAML is not a dependency of this project, so
there is no YAML parser available at test time, and these invariants are all
about the literal structure of the two files.
"""

from __future__ import annotations

import re
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
WORKFLOW_PATH = REPO_ROOT / ".github" / "workflows" / "ci.yml"
ACTION_PATH = REPO_ROOT / ".github" / "actions" / "setup-uv-python" / "action.yml"

# A job key sits at two-space indentation inside `jobs:`.
JOB_KEY_RE = re.compile(r"^  (?P<id>[A-Za-z0-9_-]+):$")
USES_RE = re.compile(r"^\s*(?:-\s*)?uses:\s*(?P<ref>\S+)\s*$", re.MULTILINE)
SHA_PIN_RE = re.compile(r"^[^@\s]+@[0-9a-f]{40}$")


def _jobs(text: str) -> dict[str, str]:
    """Split the `jobs:` mapping of a workflow into one text block per job."""
    lines = text.splitlines()
    start = next(index for index, line in enumerate(lines) if line == "jobs:")
    starts: list[tuple[str, int]] = []
    for index in range(start + 1, len(lines)):
        match = JOB_KEY_RE.match(lines[index])
        if match:
            starts.append((match.group("id"), index))

    jobs: dict[str, str] = {}
    for position, (job_id, job_start) in enumerate(starts):
        job_end = len(lines)
        if position + 1 < len(starts):
            job_end = starts[position + 1][1]
        jobs[job_id] = "\n".join(lines[job_start:job_end])
    return jobs


def _self_hosted_jobs(jobs: dict[str, str]) -> dict[str, str]:
    """Every job that runs on the persistent mac-arm64 self-hosted runners."""
    return {
        job_id: block
        for job_id, block in jobs.items()
        if re.search(r"^    runs-on:\s*\[self-hosted, mac-arm64\]", block, re.MULTILINE)
    }


def _env_value(block: str, name: str) -> str:
    """The value of the single `env:` entry called `name` in a job block."""
    matches = re.findall(rf"^\s+{re.escape(name)}:\s*(?P<value>.+)$", block, re.MULTILINE)
    assert len(matches) == 1, f"expected exactly one {name!r} env entry, found {len(matches)}"
    return matches[0].strip()


def _job_level_env(block: str) -> str:
    """The text of the job-level `env:` mapping (four-space indentation)."""
    lines = block.splitlines()
    start = next(index for index, line in enumerate(lines) if line == "    env:")
    collected = [lines[start]]
    for line in lines[start + 1 :]:
        if not line.startswith("      "):
            break
        collected.append(line)
    return "\n".join(collected)


def _workflow() -> str:
    return WORKFLOW_PATH.read_text()


def _action() -> str:
    return ACTION_PATH.read_text()


def test_workflow_exists() -> None:
    assert WORKFLOW_PATH.is_file(), f"missing {WORKFLOW_PATH}"
    assert ACTION_PATH.is_file(), f"missing {ACTION_PATH}"


# ---------------------------------------------------------------------------
# B1: untrusted fork code must never reach the credential-bearing runner.
# ---------------------------------------------------------------------------


def test_every_self_hosted_job_refuses_fork_pull_requests() -> None:
    """A self-hosted leg must be skipped unless the branch is in this repo."""
    jobs = _jobs(_workflow())
    self_hosted = _self_hosted_jobs(jobs)
    assert self_hosted, "no self-hosted job found - the workflow was restructured?"

    for job_id, block in self_hosted.items():
        guard = re.search(r"^    if:\s*(?P<expr>.+)$", block, re.MULTILINE)
        assert guard is not None, f"{job_id} has no job-level if: guard"
        expression = guard.group("expr")
        assert "github.event_name != 'pull_request'" in expression, (
            f"{job_id} must let non-pull_request events through"
        )
        assert "github.event.pull_request.head.repo.full_name == github.repository" in (
            expression
        ), f"{job_id} must refuse pull requests whose head is in another repository"


def test_hosted_fallback_covers_every_self_hosted_pipeline() -> None:
    """A skipped self-hosted leg must still produce a green required check."""
    jobs = _jobs(_workflow())
    for hosted_job, self_hosted_job in (
        ("ci", "_ci-self-hosted"),
        ("security", "_security-self-hosted"),
        ("docs", "_docs-self-hosted"),
    ):
        block = jobs[hosted_job]
        assert f"needs: {self_hosted_job}" in block
        assert "if: always()" in block
        assert f"needs.{self_hosted_job}.outputs.passed != 'true'" in block


def test_workflow_never_uses_pull_request_target() -> None:
    assert "pull_request_target" not in _workflow()


# ---------------------------------------------------------------------------
# H1: uv is a declared, pinned dependency - never ambient host state.
# ---------------------------------------------------------------------------


def test_workflow_installs_a_sha_pinned_uv() -> None:
    assert re.search(r"uses:\s*astral-sh/setup-uv@[0-9a-f]{40}", _workflow())


def test_workflow_pins_the_uv_version_to_a_literal() -> None:
    setup_uv = re.search(
        r"uses:\s*astral-sh/setup-uv@[0-9a-f]{40}\s*\n\s*with:\s*\n\s*version:\s*(?P<v>\S+)",
        _workflow(),
    )
    assert setup_uv is not None, "the setup-uv step must pin an explicit version"
    version = setup_uv.group("v").strip("\"'")
    assert version != "latest", "the uv version must be pinned, not 'latest'"
    assert re.fullmatch(r"\d+\.\d+\.\d+", version), f"unpinned uv version: {version}"


def test_action_refuses_a_uv_that_is_not_the_pinned_one() -> None:
    """A drifting host toolchain must fail the job, not silently change it."""
    action = _action()
    assert "uv --version" in action
    assert re.search(r"UV_VERSION_ACTUAL", action)
    assert re.search(r"UV_VERSION_EXPECTED", action)
    assert re.search(r"!=\s*\"?\$\{?UV_VERSION_EXPECTED", action)
    assert re.search(r"exit 1", action)


def test_action_does_not_install_the_interpreter_into_the_checkout_tree() -> None:
    """The workspace is wiped by `git clean -ffdx` at the start of every job."""
    action = _action()
    assert "UV_PYTHON_INSTALL_DIR" in action
    assert not re.search(r"UV_PYTHON_INSTALL_DIR:-[^}\$]*GITHUB_WORKSPACE", action)
    assert "UV_PYTHON_INSTALL_DIR:?" in action, (
        "the install directory must be required, not defaulted into the workspace"
    )


# ---------------------------------------------------------------------------
# M1: the cache must actually cache something.
# ---------------------------------------------------------------------------


def test_managed_interpreter_lives_outside_the_checkout_cleaned_tree() -> None:
    jobs = _jobs(_workflow())
    for job_id, block in _self_hosted_jobs(jobs).items():
        value = _env_value(block, "UV_PYTHON_INSTALL_DIR")
        assert "github.workspace" not in value, f"{job_id}: the interpreter is wiped each job"
        assert "runner.tool_cache" in value, f"{job_id}: the interpreter must persist"


def test_interpreter_path_is_not_set_in_the_job_level_env_block() -> None:
    """The runner context is not available in a job-level env block."""
    jobs = _jobs(_workflow())
    for job_id, block in _self_hosted_jobs(jobs).items():
        assert "UV_PYTHON_INSTALL_DIR" not in _job_level_env(block), (
            f"{job_id}: ${{{{ runner.tool_cache }}}} does not resolve in a job-level env"
        )


def test_virtualenv_lives_outside_the_checkout_cleaned_tree() -> None:
    jobs = _jobs(_workflow())
    for job_id, block in _self_hosted_jobs(jobs).items():
        assert 'virtualenvs-in-project: "false"' in block, (
            f"{job_id}: an in-project virtualenv is wiped by the next checkout"
        )
        path = re.search(r"virtualenvs-path:\s*(?P<p>.+)$", block, re.MULTILINE)
        assert path is not None, f"{job_id}: virtualenvs-path must be set"
        value = path.group("p")
        assert "github.workspace" not in value
        assert "runner.tool_cache" in value


def test_cache_step_runs_after_the_virtualenv_exists() -> None:
    """actions/cache refuses to save a path that does not exist yet."""
    jobs = _jobs(_workflow())
    for job_id, block in _self_hosted_jobs(jobs).items():
        select = block.index("poetry env use")
        cache = block.index("actions/cache@")
        install = block.index("poetry install --with dev")
        assert select < cache < install, f"{job_id}: the cache step is misordered"


def test_cache_key_discriminates_runner_interpreter_and_lock() -> None:
    jobs = _jobs(_workflow())
    for job_id, block in _self_hosted_jobs(jobs).items():
        assert "runner.name" in block, f"{job_id}: runner.name discriminates the two Macs"
        assert "steps.python.outputs.python_key" in block
        assert "hashFiles('poetry.lock')" in block


# ---------------------------------------------------------------------------
# M2: the cache key must encode the interpreter's patch version.
# ---------------------------------------------------------------------------


def test_cache_key_distinguishes_the_interpreter_patch_version() -> None:
    """uv keeps one install directory per minor version, so the path is not enough."""
    assert "platform.python_version()" in _action()


# ---------------------------------------------------------------------------
# M3: the managed interpreter must still win after PATH is mutated.
# ---------------------------------------------------------------------------


def test_action_exports_the_managed_interpreter_directory() -> None:
    assert "python_dir=" in _action()


def test_managed_interpreter_is_reasserted_after_the_path_mutating_step() -> None:
    jobs = _jobs(_workflow())
    for job_id, block in _self_hosted_jobs(jobs).items():
        install_poetry = block.index("snok/install-poetry@")
        assert "steps.python.outputs.python_dir" in block, (
            f"{job_id}: the managed interpreter must be re-asserted"
        )
        assert install_poetry < block.index("steps.python.outputs.python_dir"), (
            f"{job_id}: the re-assertion must come after the step that mutates PATH"
        )


# ---------------------------------------------------------------------------
# M4: mutable action tags are a credential-theft path on this fleet.
# ---------------------------------------------------------------------------


def test_every_action_reference_is_sha_pinned() -> None:
    for path in (WORKFLOW_PATH, ACTION_PATH):
        for match in USES_RE.finditer(path.read_text()):
            reference = match.group("ref")
            if reference.startswith("./"):
                continue
            assert SHA_PIN_RE.match(reference), f"{path.name}: {reference} is not SHA-pinned"


# ---------------------------------------------------------------------------
# L1 / L2: superseded runs must not occupy the fleet, and the timeout comment
# must not over-promise.
# ---------------------------------------------------------------------------


def test_workflow_declares_a_concurrency_group() -> None:
    workflow = _workflow()
    assert re.search(r"^concurrency:", workflow, re.MULTILINE)
    assert "cancel-in-progress: true" in workflow


def test_timeout_comment_states_that_the_queue_phase_is_not_bounded() -> None:
    jobs = _jobs(_workflow())
    for job_id, block in _self_hosted_jobs(jobs).items():
        assert "timeout-minutes:" in block
        timeout_line = block.index("timeout-minutes:")
        assert "queue" in block[:timeout_line], (
            f"{job_id}: the comment must say the timeout does not bound the queue"
        )
