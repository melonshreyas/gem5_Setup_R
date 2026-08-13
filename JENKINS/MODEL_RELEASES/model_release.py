#!/usr/bin/env python3
"""Collect, build, simulate, and record a gem5 model release."""

from __future__ import annotations

import argparse
import json
import re
import shlex
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

from model_release_email import send_release_report_email
from model_release_html import write_release_report

RELEASE_ROOT = Path("/Users/diya/Documents/JENKINS/HISTORY/MODEL_RELEASES")
DEFAULT_REPO_URL = "https://github.com/melonshreyas/gem5_Setup_R.git"
ALLOWED_MODEL_UNITS = {
    "IFU",
    "BPU",
    "IDU",
    "DISPATCH_UNIT",
    "RENAME_UNIT",
    "ISSUE_QUEUE",
    "COMPLETION_UNIT",
    "FXU",
    "ALU",
    "FPU",
    "VSX",
    "CRU",
    "LSU",
    "EA_GENERATION",
    "L1_ICACHE",
    "L1_DCACHE",
    "L2_CACHE",
    "DTLB",
    "PREFETCH_ENGINE",
    "MEMORY_CONTROLLER",
    "COHERENCE_ENGINE",
    "NEST_INTERCONNECT",
    "PCIe_CONTROLLER",
    "CAPI_INTERFACE",
    "NVLINK_INTERFACE",
    "SMT_SCHEDULER",
}
DEFAULT_CHIP_CONFIGURATION = Path(__file__).resolve().parents[1] / "SMOKE" / "chip_configuration.json"


def required_text(value: str, field_name: str) -> str:
    cleaned = str(value or "").strip()
    if not cleaned:
        raise ValueError(f"Release blocked: {field_name} is required.")
    return cleaned


def run(command: List[str], cwd: Path, log_path: Optional[Path] = None) -> subprocess.CompletedProcess[str]:
    completed = subprocess.run(command, cwd=cwd, text=True, capture_output=True, check=False)
    if log_path:
        log_path.parent.mkdir(parents=True, exist_ok=True)
        log_path.write_text(completed.stdout + completed.stderr, encoding="utf-8")
    return completed


def git_value(command: List[str], cwd: Path) -> str:
    result = run(command, cwd)
    if result.returncode:
        raise RuntimeError(result.stderr.strip() or "Git command failed")
    return result.stdout.strip()


def load_config(path: Path) -> Dict[str, Any]:
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError("Chip configuration must contain a JSON object.")
    return data


def select_chips(config: Dict[str, Any], requested: Optional[str]) -> List[str]:
    names = [name.strip() for name in (requested or "ALL").split(",") if name.strip()]
    if not names or any(name.upper() == "ALL" for name in names):
        return [name for name, value in config.items() if isinstance(value, dict)]
    unknown = [name for name in names if name not in config]
    if unknown:
        raise ValueError(f"Release blocked: unknown CHIP_NAME value(s): {', '.join(unknown)}")
    return names


def expand_cases(chip_config: Dict[str, Any], requested: Optional[str]) -> List[tuple[str, Dict[str, Any]]]:
    tests = chip_config.get("simulate", {}).get("tests", {})
    if not isinstance(tests, dict):
        return []
    requested_names = [name.strip() for name in (requested or "ALL").split(",") if name.strip()]
    if not requested_names or any(name.upper() == "ALL" for name in requested_names):
        return [(name, value) for name, value in tests.items() if isinstance(value, dict)]
    unknown = [name for name in requested_names if name not in tests]
    if unknown:
        raise ValueError(f"Release blocked: unknown TESTCASE value(s): {', '.join(unknown)}")
    return [(name, tests[name]) for name in requested_names]


def run_testcase(repo_dir: Path, output_dir: Path, binary: Path, chip: str, testcase: str, case_config: Dict[str, Any]) -> Dict[str, Any]:
    case_dir = output_dir / "RESULTS" / "simulation" / chip / testcase
    case_dir.mkdir(parents=True, exist_ok=True)
    script = repo_dir / str(case_config.get("sim_script", ""))
    if not script.exists():
        return {"status": "SKIP", "reason": f"Simulation script not found: {script}", "output_dir": str(case_dir)}
    args = [str(token) for token in case_config.get("sim_script_args", [])]
    args = [token for token in args if not token.startswith("--outdir") and not token.startswith("--workload")]
    command = [str(binary), f"--outdir={case_dir}", "--redirect-stdout", "--redirect-stderr", str(script), *args]
    started = time.perf_counter()
    result = run(command, repo_dir, case_dir / "simulation.log")
    return {
        "status": "PASS" if result.returncode == 0 else "FAIL",
        "return_code": result.returncode,
        "runtime_seconds": round(time.perf_counter() - started, 3),
        "command": command,
        "output_dir": str(case_dir),
        "stats_file": str(case_dir / "stats.txt"),
    }


def next_release_version(unit_dir: Path, model_unit_name: str, create_unit_dir: bool = True) -> str:
    """Return the next immutable version name, for example IFU_1 or IFU_2."""
    if create_unit_dir:
        unit_dir.mkdir(parents=True, exist_ok=True)
    if not unit_dir.exists():
        return f"{model_unit_name}_1"
    pattern = re.compile(rf"^{re.escape(model_unit_name)}_(\d+)$")
    numbers = []
    for child in unit_dir.iterdir():
        if child.is_dir():
            match = pattern.fullmatch(child.name)
            if match:
                numbers.append(int(match.group(1)))
    return f"{model_unit_name}_{max(numbers, default=0) + 1}"


def dry_run_release(args: argparse.Namespace) -> int:
    """Plan a release without creating, cloning, compiling, or simulating."""
    model_unit_name = str(args.model_unit_name).strip().upper()
    branch = required_text(args.branch, "BRANCH")
    summary = required_text(args.summary, "SUMMARY")
    fixes = required_text(args.fixes, "FIXES")
    config_path = Path(args.chip_configuration).expanduser().resolve()
    config = load_config(config_path)
    selected_chips = select_chips(config, args.chip_name)
    release_version = next_release_version(RELEASE_ROOT / model_unit_name, model_unit_name, create_unit_dir=False)
    release_dir = RELEASE_ROOT / model_unit_name / release_version
    target = "gem5.opt" if args.compile == "opt" else "gem5.debug"
    source_dir = release_dir / "source"
    binary = source_dir / "build" / "ALL" / target

    commands: List[List[str]] = [
        ["git", "clone", "--recursive", "--branch", branch, args.repo_url, str(source_dir)],
        ["scons", f"build/ALL/{target}", "-j20", "--ignore-style", "--install-hooks"],
    ]
    testcase_plan: Dict[str, List[str]] = {}
    for chip in selected_chips:
        testcase_plan[chip] = []
        for testcase, case_config in expand_cases(config[chip], args.testcase):
            testcase_plan[chip].append(testcase)
            case_dir = release_dir / "RESULTS" / "simulation" / chip / testcase
            script = source_dir / str(case_config.get("sim_script", ""))
            case_args = [str(token) for token in case_config.get("sim_script_args", [])]
            case_args = [token for token in case_args if not token.startswith("--outdir") and not token.startswith("--workload")]
            commands.append([str(binary), f"--outdir={case_dir}", "--redirect-stdout", "--redirect-stderr", str(script), *case_args])

    preview_dir = Path.cwd() / "model_release_dry_run"
    preview_dir.mkdir(parents=True, exist_ok=True)
    command_lines = [" ".join(shlex.quote(token) for token in command) for command in commands]
    log_path = preview_dir / "dry_run.log"
    log_path.write_text(
        "MODEL RELEASE DRY RUN\n"
        f"MODEL_UNIT_NAME: {model_unit_name}\n"
        f"RELEASE_VERSION: {release_version}\n"
        f"RELEASE_DIRECTORY: {release_dir}\n"
        f"CHIP_CONFIGURATION: {config_path}\n\n"
        + "\n".join(f"COMMAND {index}: {command}" for index, command in enumerate(command_lines, 1))
        + "\n",
        encoding="utf-8",
    )
    preview = {
        "mode": "dry_run",
        "model_unit_name": model_unit_name,
        "release_version": release_version,
        "release_directory": str(release_dir),
        "branch": branch,
        "repo_url": args.repo_url,
        "chip_configuration": str(config_path),
        "selected_chips": selected_chips,
        "testcases": testcase_plan,
        "compile_target": target,
        "summary": summary,
        "fixes": fixes,
        "commands": command_lines,
        "log_file": str(log_path),
        "note": "Dry run only: no release directory, clone, compilation, simulation, or email was performed.",
    }
    preview_path = preview_dir / "dry_run_manifest.json"
    preview_path.write_text(json.dumps(preview, indent=2) + "\n", encoding="utf-8")
    print("[DRY RUN] No release files or commands were executed.")
    print(f"[DRY RUN] Planned release: {release_dir}")
    print(f"[DRY RUN] Selected chips: {', '.join(selected_chips)}")
    for chip, testcases in testcase_plan.items():
        print(f"[DRY RUN] {chip} testcases: {', '.join(testcases)}")
    for index, command in enumerate(command_lines, 1):
        print(f"[DRY RUN] COMMAND {index}: {command}")
    print(f"[DRY RUN] Manifest: {preview_path}")
    print(f"[DRY RUN] Log: {log_path}")
    return 0


def collect_release(args: argparse.Namespace) -> Path:
    model_unit_name = required_text(args.model_unit_name, "MODEL_UNIT_NAME").upper()
    if model_unit_name not in ALLOWED_MODEL_UNITS:
        raise ValueError(f"Release blocked: unsupported MODEL_UNIT_NAME '{model_unit_name}'.")

    branch = required_text(args.branch, "BRANCH")
    summary = required_text(args.summary, "SUMMARY")
    fixes = required_text(args.fixes, "FIXES")

    unit_dir = RELEASE_ROOT / model_unit_name
    release_version = next_release_version(unit_dir, model_unit_name)
    release_dir = unit_dir / release_version
    if release_dir.exists() and any(release_dir.iterdir()):
        raise ValueError(f"Release blocked: generated version already exists: {release_dir}")
    release_dir.mkdir(parents=True, exist_ok=True)

    repo_dir = release_dir / "source"
    if not repo_dir.exists():
        clone = run(["git", "clone", "--recursive", "--branch", branch, args.repo_url, str(repo_dir)], release_dir, release_dir / "clone.log")
        if clone.returncode:
            raise RuntimeError(clone.stderr.strip() or "Source clone failed")
    else:
        run(["git", "fetch", "--all", "--prune"], repo_dir)
        run(["git", "checkout", branch], repo_dir)
        run(["git", "submodule", "update", "--init", "--recursive"], repo_dir)

    config_path = Path(args.chip_configuration).expanduser().resolve() if args.chip_configuration else DEFAULT_CHIP_CONFIGURATION
    config = load_config(config_path)
    selected_chips = select_chips(config, args.chip_name)
    target = "gem5.opt" if args.compile == "opt" else "gem5.debug"
    build_log = release_dir / "RESULTS" / "compilation" / f"compile_{args.compile}.log"
    build_log.parent.mkdir(parents=True, exist_ok=True)
    started = time.perf_counter()
    compile_result = run(["scons", f"build/ALL/{target}", "-j20", "--ignore-style", "--install-hooks"], repo_dir, build_log)
    binary = repo_dir / "build" / "ALL" / target
    if compile_result.returncode or not binary.exists():
        raise RuntimeError(f"Compilation failed; see {build_log}")

    chip_results: Dict[str, Any] = {}
    for chip in selected_chips:
        chip_results[chip] = {}
        for testcase, case_config in expand_cases(config[chip], args.testcase):
            chip_results[chip][testcase] = run_testcase(repo_dir, release_dir, binary, chip, testcase, case_config)

    manifest: Dict[str, Any] = {
        "release_name": f"{model_unit_name}-{release_version}",
        "version": release_version,
        "model_unit_name": model_unit_name,
        "branch": branch,
        "commit_id": git_value(["git", "rev-parse", "HEAD"], repo_dir),
        "created_at": datetime.now(timezone.utc).isoformat(),
        "status": "validated",
        "summary": summary,
        "fixes": fixes,
        "source_directory": str(repo_dir),
        "release_directory": str(release_dir),
        "chip_configuration": str(config_path),
        "selected_chips": selected_chips,
        "testcase_filter": args.testcase or "ALL",
        "compile": {"target": target, "runtime_seconds": round(time.perf_counter() - started, 3), "log_file": str(build_log)},
        "simulation": chip_results,
        "notes": "Testcases come from chip_configuration.json. Existing unit folders are reused; each automatically generated model-unit version creates one immutable version folder.",
    }
    (release_dir / "release_manifest.json").write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    (release_dir / "RELEASE_NOTES.md").write_text(
        f"# {model_unit_name} model release\n\n"
        f"- Version: `{release_version}`\n"
        f"- Model unit: `{model_unit_name}`\n"
        f"- Branch: `{branch}`\n\n"
        f"## Summary\n\n{summary}\n\n"
        f"## Fixes\n\n{fixes}\n",
        encoding="utf-8",
    )
    report_path = write_release_report(release_dir, manifest)
    manifest["report_file"] = str(report_path)
    (release_dir / "release_manifest.json").write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")

    if args.send_email:
        sent = send_release_report_email(
            report_path=report_path,
            recipients=args.recipient_email,
            smtp_server=args.smtp_server,
            smtp_port=args.smtp_port,
            sender_email=args.sender_email,
            sender_password=args.sender_password,
            subject=args.email_subject or f"Model release {model_unit_name} {release_version}",
        )
        if not sent:
            raise RuntimeError("Release email delivery failed; check SMTP settings and credentials.")
    return release_dir


def parse_smtp_port(value: str) -> int:
    """Validate the SMTP port supplied to the release email module."""
    try:
        port = int(value)
    except ValueError as exc:
        raise argparse.ArgumentTypeError("SMTP port must be an integer.") from exc
    if not 1 <= port <= 65535:
        raise argparse.ArgumentTypeError("SMTP port must be between 1 and 65535.")
    return port


def parse_args() -> argparse.Namespace:
    """Parse command-line options for the model-release workflow.

    The parser is intentionally usable both from Jenkins and from a terminal.
    CHIP_NAME and TESTCASE accept ALL, one name, or comma-separated names.
    """
    parser = argparse.ArgumentParser(
        prog="model_release.py",
        description=(
            "Create the next immutable gem5 model release by cloning, compiling, "
            "simulating, reporting, and optionally emailing the release report."
        ),
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument(
        "--model-unit-name",
        required=True,
        choices=sorted(ALLOWED_MODEL_UNITS),
        help="POWER9 pipeline/model unit to release.",
    )
    parser.add_argument(
        "--branch",
        required=True,
        help="Git branch to clone or update.",
    )
    parser.add_argument(
        "--summary",
        required=True,
        help="Release summary text.",
    )
    parser.add_argument(
        "--fixes",
        required=True,
        help="Fixes and changes included in this release.",
    )
    parser.add_argument(
        "--repo-url",
        default=DEFAULT_REPO_URL,
        help="Git repository URL used for the release source.",
    )
    parser.add_argument(
        "--chip-configuration",
        type=Path,
        default=DEFAULT_CHIP_CONFIGURATION,
        help="Path to the unit/chip/testcase JSON configuration.",
    )
    parser.add_argument(
        "--chip-name",
        default="ALL",
        help="Chip filter: ALL, one chip, or comma-separated chip names.",
    )
    parser.add_argument(
        "--testcase",
        default="ALL",
        help="Testcase filter: ALL, one testcase, or comma-separated testcase names.",
    )
    parser.add_argument(
        "--compile",
        choices=["opt", "debug"],
        default="opt",
        help="gem5 binary target to compile.",
    )
    parser.add_argument(
        "--send-email",
        action="store_true",
        help="Email the generated unit/version HTML report.",
    )
    parser.add_argument("--smtp-server", default=None, help="SMTP server hostname.")
    parser.add_argument(
        "--smtp-port",
        type=parse_smtp_port,
        default=587,
        help="SMTP server port.",
    )
    parser.add_argument("--sender-email", default=None, help="SMTP sender email address.")
    parser.add_argument("--sender-password", default=None, help="SMTP password or app password.")
    parser.add_argument(
        "--recipient-email",
        action="append",
        default=None,
        help="Recipient address; repeat for multiple recipients.",
    )
    parser.add_argument(
        "--email-subject",
        default=None,
        help="Email subject. Defaults to the generated model-unit/version name.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Print planned clone/compile/simulation commands and write a preview without executing anything.",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    try:
        if args.dry_run:
            return dry_run_release(args)
        release_dir = collect_release(args)
    except (OSError, subprocess.CalledProcessError, ValueError, RuntimeError) as exc:
        print(f"[RELEASE BLOCKED] {exc}")
        return 1
    print(f"[RELEASE READY] {release_dir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
