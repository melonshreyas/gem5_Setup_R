#!/usr/bin/env python3
"""Smoke test workflow for the gem5 setup repository.

This script provides a simple, structured entry point for:
- cloning a repository,
- collecting git metadata,
- compiling gem5,
- and running a smoke-style simulation step.

The implementation follows a UVM-style logging pattern with WARNING, DEBUG,
ERROR, and FATAL helpers, and it exposes a command-line interface for the
requested input/output paths, branch selection, and chip configuration.
"""

from __future__ import annotations

import argparse
import json
import re
import shutil
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

from jenkins_weekly_html import (
    generate_jenkins_history_weekly_results_html,
    generate_jenkins_history_weekly_results_json,
    generate_weekly_results_html,
    generate_weekly_results_json,
)
from send_email_report import send_history_report_email

DEFAULT_INPUT_DIR = Path("/Users/diya/Documents/JENKINS/SMOKE")
DEFAULT_REPO_URL = "https://github.com/melonshreyas/gem5_Setup_R.git"
DEFAULT_HISTORY_DIR = Path("/Users/diya/Documents/JENKINS/HISTORY/WEEKLY_REGRESSION")
DEFAULT_GOLDEN_DIR = Path("/Users/diya/Documents/JENKINS/HISTORY/GOLDEN/WEEKLY_REGRESSION")
COMPILE_ERROR_PATTERNS = (
    r"\berror:\s+",
    r"\bfatal error:\s+",
    r"\bfatal error\b",
    r"\berror\b",
    r"\bundefined reference to\b",
    r"\bcollect2:\s+error:\s+ld returned 1 exit status\b",
    r"\bscons:\s+\*\*\*",
    r"\bscons:\s+building terminated because of errors\b",
    r"\bcompilation terminated\b",
    r"\bzlib compression\b",
    r"\bvariable length arrays?\b",
    r"\bclang extension\b",
    r"\bcheck failed.*python\.h\b",
    r"\btraceback \(most recent call last\):",
)
STATS_METRIC_PATTERNS = {
    "simSeconds": re.compile(r"^simSeconds\s+([0-9.eE+-]+)", re.MULTILINE),
    "simTicks": re.compile(r"^simTicks\s+([0-9.eE+-]+)", re.MULTILINE),
    "finalTick": re.compile(r"^finalTick\s+([0-9.eE+-]+)", re.MULTILINE),
    "simFreq": re.compile(r"^simFreq\s+([0-9.eE+-]+)", re.MULTILINE),
    "hostSeconds": re.compile(r"^hostSeconds\s+([0-9.eE+-]+)", re.MULTILINE),
    "hostTickRate": re.compile(r"^hostTickRate\s+([0-9.eE+-]+)", re.MULTILINE),
    "hostMemory": re.compile(r"^hostMemory\s+([0-9.eE+-]+)", re.MULTILINE),
}

EXTRA_CLUSTER_METRIC_PATTERNS = {
    "l1dcache.overallMisses_total": re.compile(
        r"^board\.cache_hierarchy\.clusters(?P<cluster>\d+)\.l1dcache\.overallMisses::total\s+([0-9.eE+-]+)",
        re.MULTILINE,
    ),
    "l1dcache.overallAccesses_total": re.compile(
        r"^board\.cache_hierarchy\.clusters(?P<cluster>\d+)\.l1dcache\.overallAccesses::total\s+([0-9.eE+-]+)",
        re.MULTILINE,
    ),
    "l1dcache.writebacks_total": re.compile(
        r"^board\.cache_hierarchy\.clusters(?P<cluster>\d+)\.l1dcache\.writebacks::total\s+([0-9.eE+-]+)",
        re.MULTILINE,
    ),
    "l1dcache.demandMshrHits_total": re.compile(
        r"^board\.cache_hierarchy\.clusters(?P<cluster>\d+)\.l1dcache\.demandMshrHits::total\s+([0-9.eE+-]+)",
        re.MULTILINE,
    ),
    "l1dcache.overallMshrHits_total": re.compile(
        r"^board\.cache_hierarchy\.clusters(?P<cluster>\d+)\.l1dcache\.overallMshrHits::total\s+([0-9.eE+-]+)",
        re.MULTILINE,
    ),
    "l1dcache.demandMshrMisses_total": re.compile(
        r"^board\.cache_hierarchy\.clusters(?P<cluster>\d+)\.l1dcache\.demandMshrMisses::total\s+([0-9.eE+-]+)",
        re.MULTILINE,
    ),
    "l1dcache.overallMshrMisses_total": re.compile(
        r"^board\.cache_hierarchy\.clusters(?P<cluster>\d+)\.l1dcache\.overallMshrMisses::total\s+([0-9.eE+-]+)",
        re.MULTILINE,
    ),
    "l1dcache.replacements": re.compile(
        r"^board\.cache_hierarchy\.clusters(?P<cluster>\d+)\.l1dcache\.replacements\s+([0-9.eE+-]+)",
        re.MULTILINE,
    ),
    "l1dcache.prefetcher.pfIssued": re.compile(
        r"^board\.cache_hierarchy\.clusters(?P<cluster>\d+)\.l1dcache\.prefetcher\.pfIssued\s+([0-9.eE+-]+)",
        re.MULTILINE,
    ),
    "l1dcache.prefetcher.pfUseful": re.compile(
        r"^board\.cache_hierarchy\.clusters(?P<cluster>\d+)\.l1dcache\.prefetcher\.pfUseful\s+([0-9.eE+-]+)",
        re.MULTILINE,
    ),
    "l1dcache.prefetcher.pfUsefulButMiss": re.compile(
        r"^board\.cache_hierarchy\.clusters(?P<cluster>\d+)\.l1dcache\.prefetcher\.pfUsefulButMiss\s+([0-9.eE+-]+)",
        re.MULTILINE,
    ),
    "l1icache.replacements": re.compile(
        r"^board\.cache_hierarchy\.clusters(?P<cluster>\d+)\.l1icache\.replacements\s+([0-9.eE+-]+)",
        re.MULTILINE,
    ),
    "l1icache.prefetcher.pfIssued": re.compile(
        r"^board\.cache_hierarchy\.clusters(?P<cluster>\d+)\.l1icache\.prefetcher\.pfIssued\s+([0-9.eE+-]+)",
        re.MULTILINE,
    ),
    "l1icache.prefetcher.pfUseful": re.compile(
        r"^board\.cache_hierarchy\.clusters(?P<cluster>\d+)\.l1icache\.prefetcher\.pfUseful\s+([0-9.eE+-]+)",
        re.MULTILINE,
    ),
    "l1icache.prefetcher.pfUsefulButMiss": re.compile(
        r"^board\.cache_hierarchy\.clusters(?P<cluster>\d+)\.l1icache\.prefetcher\.pfUsefulButMiss\s+([0-9.eE+-]+)",
        re.MULTILINE,
    ),
    "l2_bus.pktCount_total": re.compile(
        r"^board\.cache_hierarchy\.clusters(?P<cluster>\d+)\.l2_bus\.pktCount::total\s+([0-9.eE+-]+)",
        re.MULTILINE,
    ),
    "l2cache.demandMisses_total": re.compile(
        r"^board\.cache_hierarchy\.clusters(?P<cluster>\d+)\.l2cache\.demandMisses::total\s+([0-9.eE+-]+)",
        re.MULTILINE,
    ),
    "l2cache.overallMisses_total": re.compile(
        r"^board\.cache_hierarchy\.clusters(?P<cluster>\d+)\.l2cache\.overallMisses::total\s+([0-9.eE+-]+)",
        re.MULTILINE,
    ),
    "l2cache.replacements": re.compile(
        r"^board\.cache_hierarchy\.clusters(?P<cluster>\d+)\.l2cache\.replacements\s+([0-9.eE+-]+)",
        re.MULTILINE,
    ),
}

EXTRA_CORE_GENERATOR_METRICS = (
    "numPackets",
    "numRetries",
    "totalReads",
    "totalWrites",
    "readBW",
    "writeBW",
)

# Extra cluster/generator metrics are testcase-specific and can be noisy for
# non-cache flows, so only collect them for relevant testcase names.
EXTRA_METRICS_TESTCASES = {
    "smoke_test_cache_materials",
}


def _parse_stat_number(value_text: str) -> Any:
    """Convert a stats token to int/float when possible."""
    token = str(value_text).strip()
    try:
        return int(token)
    except ValueError:
        try:
            return float(token)
        except ValueError:
            return token


class SmokeLogger:
    """Simple UVM-style logger with WARNING, DEBUG, ERROR, and FATAL helpers."""

    def __init__(self, verbose: bool = False) -> None:
        """Initialize the logger with optional verbose mode.
        This keeps the workflow output readable while enabling extra detail when requested.
        """
        self.verbose = verbose

    def _emit(self, level: str, message: str) -> None:
        """Emit a log line with the requested severity.
        This is the shared output path used by the other logging helpers.
        """
        print(f"[{level}] {message}")

    def warning(self, message: str) -> None:
        """Log a warning-level message.
        Warnings highlight important but non-fatal workflow conditions.
        """
        self._emit("WARNING", message)

    def debug(self, message: str) -> None:
        """Log a debug message when verbose mode is enabled.
        These messages are only printed when the user asks for verbose output.
        """
        if self.verbose:
            self._emit("DEBUG", message)

    def error(self, message: str) -> None:
        """Log an error-level message.
        Errors indicate a step failed but the script may continue to report the state.
        """
        self._emit("ERROR", message)

    def fatal(self, message: str) -> None:
        """Log a fatal message and stop the workflow with an exception.
        This is used when the run cannot continue safely.
        """
        self._emit("FATAL", message)
        raise RuntimeError(message)


def parse_bool(value: Any) -> bool:
    """Parse a boolean-like CLI value.
    This accepts common forms such as true/false and 1/0 from the command line.
    """
    if isinstance(value, bool):
        return value
    if value is None:
        return False

    normalized = str(value).strip().lower()
    if normalized in {"1", "true", "yes", "y", "on"}:
        return True
    if normalized in {"0", "false", "no", "n", "off"}:
        return False
    raise argparse.ArgumentTypeError(f"Unsupported boolean value: {value}")


def parse_args() -> argparse.Namespace:
    """Parse the command-line options for the smoke workflow.
    This makes the build, run, reporting, and email behavior configurable from the shell.
    """
    parser = argparse.ArgumentParser(
        description="Run a gem5 smoke workflow with repository clone, compile, and simulation steps."
    )
    parser.add_argument(
        "--input-dir",
        default=str(DEFAULT_INPUT_DIR),
        help="Base directory where the repository workspace will be created. Default: %(default)s",
    )
    parser.add_argument(
        "--output-dir",
        default=None,
        help="Directory used for compilation and simulation outputs. Defaults to a new WEEKLY_BUILD_<NUM> folder under the input directory.",
    )
    parser.add_argument(
        "--branch",
        default="main",
        help="Branch to check out after cloning. Default: %(default)s",
    )
    parser.add_argument(
        "--chip-configuration",
        default=None,
        help="Path to a JSON file that contains chip or simulation configuration settings.",
    )
    parser.add_argument(
        "--compile",
        choices=["opt", "debug"],
        default="opt",
        help="Which gem5 build target to compile. Default: %(default)s",
    )
    parser.add_argument(
        "--chip-name",
        nargs="*",
        default=None,
        help="Optional chip names to process from the chip configuration JSON. If omitted or empty, all chip entries are processed. You can provide multiple names, for example: --chip-name CHIP_1 CHIP_2.",
    )
    parser.add_argument(
        "--skip-compilation",
        "--skip_compilation",
        dest="skip_compilation",
        nargs="?",
        const=True,
        default=False,
        type=parse_bool,
        help="Skip the compilation step entirely. Use --skip-compilation to enable it, or --skip-compilation true/false to set the value explicitly. Default: %(default)s",
    )
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Enable verbose debug logging.",
    )
    parser.add_argument(
        "--skip_simulation",
        action="store_true",
        help="Skip the simulation phase and still generate summary, HTML, and JSON reports with default placeholder rows.",
    )
    parser.add_argument(
        "--dry_run",
        action="store_true",
        help="Generate the planned compile and simulation commands without running any subprocesses.",
    )
    parser.add_argument(
        "--send-email",
        action="store_true",
        help="Send the generated history HTML report by email after the workflow completes.",
    )
    parser.add_argument(
        "--smtp-server",
        default=None,
        help="SMTP server hostname for email delivery. Can also be supplied via SMTP_SERVER.",
    )
    parser.add_argument(
        "--smtp-port",
        type=int,
        default=587,
        help="SMTP server port for email delivery. Default: %(default)s",
    )
    parser.add_argument(
        "--sender-email",
        default=None,
        help="Email address used to send the report. Can also be supplied via SENDER_EMAIL.",
    )
    parser.add_argument(
        "--sender-password",
        default=None,
        help="Password or app-specific password for the sender account. Can also be supplied via SENDER_PASSWORD.",
    )
    parser.add_argument(
        "--recipient-email",
        action="append",
        default=None,
        help="Recipient email address for the report. Repeat the flag for multiple recipients. Can also be supplied via SMTP_RECIPIENTS.",
    )
    parser.add_argument(
        "--email-subject",
        default="gem5 Smoke Report",
        help="Email subject for the sent report. Default: %(default)s",
    )
    parser.add_argument(
        "--lsf",
        type=int,
        choices=[0, 1],
        default=0,
        help="Choose execution mode: 0 for local execution, 1 to submit a bsub job. Default: %(default)s",
    )
    parser.add_argument(
        "--lsf-queue",
        default="normal",
        help="LSF queue name to use when --lsf 1 is selected. Default: %(default)s",
    )
    parser.add_argument(
        "--lsf-memory",
        default="64GB",
        help="Requested memory for the LSF job when --lsf 1 is selected. Default: %(default)s",
    )
    parser.add_argument(
        "--lsf-walltime",
        default="24:00",
        help="Walltime for the LSF job when --lsf 1 is selected. Default: %(default)s",
    )
    return parser.parse_args()


def build_lsf_submission_command(args: argparse.Namespace, output_dir: Path, logger: SmokeLogger) -> List[str]:
    """Create an LSF submission command for the workflow.
    This preserves the selected options when the run is forwarded to bsub.
    """
    command = [
        "bsub",
        "-q",
        args.lsf_queue,
        "-M",
        args.lsf_memory,
        "-W",
        args.lsf_walltime,
        "-o",
        str(output_dir / "lsf_submit.log"),
        "-e",
        str(output_dir / "lsf_submit.err"),
        "python3",
        str(Path(__file__).resolve()),
        "--input-dir",
        args.input_dir,
        "--output-dir",
        str(output_dir),
        "--branch",
        args.branch,
        "--chip-configuration",
        args.chip_configuration,
        "--compile",
        args.compile,
    ]
    chip_names = args.chip_name or []
    if chip_names:
        command.extend(["--chip-name", *chip_names])
    if args.skip_compilation:
        command.append("--skip-compilation")
    if args.skip_simulation:
        command.append("--skip_simulation")
    if args.dry_run:
        command.append("--dry_run")
    if args.send_email:
        command.append("--send-email")
    if args.smtp_server:
        command.extend(["--smtp-server", args.smtp_server])
    if args.smtp_port:
        command.extend(["--smtp-port", str(args.smtp_port)])
    if args.sender_email:
        command.extend(["--sender-email", args.sender_email])
    if args.sender_password:
        command.extend(["--sender-password", args.sender_password])
    if args.recipient_email:
        for recipient in args.recipient_email:
            command.extend(["--recipient-email", recipient])
    if args.email_subject != "gem5 Smoke Report":
        command.extend(["--email-subject", args.email_subject])
    command.extend(["--lsf", "0"])
    return command


def resolve_output_dir(input_dir: Path, requested_output_dir: Optional[str]) -> Path:
    """Resolve the output directory for the current run.
    When no path is provided, it creates a numbered smoke-build directory automatically.
    """
    if requested_output_dir:
        return Path(requested_output_dir).expanduser().resolve()

    base_dir = input_dir.expanduser().resolve()
    base_dir.mkdir(parents=True, exist_ok=True)
    index = 1
    while True:
        candidate = base_dir / f"WEEKLY_BUILD_{index}"
        if not candidate.exists():
            return candidate
        index += 1


def load_chip_configuration(path_str: Optional[str], logger: SmokeLogger) -> Dict[str, Any]:
    """Load the optional chip configuration from JSON.
    It validates the file and returns the structured chip settings for the workflow.
    """
    if not path_str:
        logger.debug("No chip configuration file was provided.")
        return {}

    config_path = Path(path_str).expanduser().resolve()
    if not config_path.exists():
        logger.fatal(f"Chip configuration file was not found: {config_path}")

    try:
        with config_path.open("r", encoding="utf-8") as handle:
            data = json.load(handle)
    except json.JSONDecodeError as exc:
        logger.fatal(f"Invalid JSON in chip configuration file: {exc}")

    if not isinstance(data, dict):
        logger.fatal("Chip configuration JSON must be an object at the top level.")

    logger.debug(f"Loaded chip configuration from {config_path}")
    return data


def run_command(
    command: List[str],
    cwd: Path,
    logger: SmokeLogger,
    allow_failure: bool = False,
    log_file: Optional[Path] = None,
    input_text: Optional[str] = None,
) -> subprocess.CompletedProcess[str]:
    """Run a subprocess and capture its output.
    The command stream is logged to disk so failures are easier to inspect later.
    """
    logger.debug(f"Running command: {' '.join(command)}")

    if log_file is not None:
        log_file.parent.mkdir(parents=True, exist_ok=True)
        log_file.write_text(
            f"COMMAND: {' '.join(command)}\n"
            f"CWD: {cwd}\n"
            f"STATE: STARTED\n\n",
            encoding="utf-8",
        )

    process = subprocess.Popen(
        command,
        cwd=str(cwd),
        text=True,
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        bufsize=1,
    )

    if input_text is not None and process.stdin is not None:
        process.stdin.write(input_text)
        process.stdin.flush()

    output_lines: List[str] = []
    if process.stdout is not None:
        for line in process.stdout:
            output_lines.append(line)
            if log_file is not None:
                log_file.parent.mkdir(parents=True, exist_ok=True)
                with log_file.open("a", encoding="utf-8") as handle:
                    handle.write(line)
            if logger.verbose:
                logger.debug(line.rstrip())

    return_code = process.wait()
    combined_output = "".join(output_lines)

    if log_file is not None:
        log_file.parent.mkdir(parents=True, exist_ok=True)
        with log_file.open("a", encoding="utf-8") as handle:
            handle.write(f"\nRETURN_CODE: {return_code}\n")

    completed = subprocess.CompletedProcess(
        args=command,
        returncode=return_code,
        stdout=combined_output,
        stderr="",
    )

    if completed.returncode != 0 and not allow_failure:
        logger.fatal(
            f"Command failed with exit code {completed.returncode}: {' '.join(command)}"
        )

    return completed


def git_clone(repo_url: str, destination_dir: Path, branch: str, logger: SmokeLogger) -> Dict[str, Any]:
    """Clone or reuse the repository and collect git metadata.
    This ensures the workflow runs against the requested checkout and captures commit details.
    """
    destination_dir.mkdir(parents=True, exist_ok=True)
    repo_dir = destination_dir

    if not (repo_dir / ".git").exists():
        logger.warning(f"Cloning repository into {repo_dir}")
        run_command(["git", "clone", "--recursive", repo_url, str(repo_dir)], cwd=destination_dir.parent, logger=logger)
    else:
        logger.warning(f"Repository already exists at {repo_dir}; git clone is done, reusing existing checkout")
        run_command(["git", "fetch", "--all", "--prune"], cwd=repo_dir, logger=logger, allow_failure=True)

    run_command(["git", "submodule", "update", "--init", "--recursive"], cwd=repo_dir, logger=logger, allow_failure=True)

    if branch:
        run_command(["git", "checkout", branch], cwd=repo_dir, logger=logger, allow_failure=True)

    metadata: Dict[str, Any] = {}
    metadata["commit_id"] = run_command(["git", "rev-parse", "HEAD"], cwd=repo_dir, logger=logger).stdout.strip()
    metadata["branch_name"] = run_command(["git", "branch", "--show-current"], cwd=repo_dir, logger=logger).stdout.strip()
    metadata["pushed_by"] = run_command(["git", "log", "-1", "--pretty=format:%an"], cwd=repo_dir, logger=logger).stdout.strip()
    metadata["changed_files"] = [
        line.strip()
        for line in run_command(["git", "status", "--short"], cwd=repo_dir, logger=logger).stdout.splitlines()
        if line.strip()
    ]

    logger.warning(f"Git commit: {metadata['commit_id']}")
    logger.warning(f"Git branch: {metadata['branch_name'] or branch}")
    logger.warning(f"Pushed by: {metadata['pushed_by'] or 'unknown'}")
    logger.warning(f"Changed files: {metadata['changed_files'] or 'none'}")

    return metadata


def should_skip_build(repo_dir: Path, gem5_binary: Path, logger: SmokeLogger) -> bool:
    """Decide whether a cached gem5 build can be reused.
    If the sources are unchanged, the expensive compile step can be skipped.
    """
    if not gem5_binary.exists():
        return False

    relevant_suffixes = (".cc", ".hh", ".h", ".py")
    source_files = []
    for path in repo_dir.rglob("*"):
        if path.is_file() and path.suffix.lower() in relevant_suffixes:
            source_files.append(path)

    if not source_files:
        return False

    newest_source = max(path.stat().st_mtime for path in source_files)
    binary_time = gem5_binary.stat().st_mtime
    if binary_time >= newest_source:
        logger.warning(f"Existing binary is up to date: {gem5_binary}")
        return True

    logger.warning("Relevant source files changed; recompilation is required.")
    return False


def read_stats_metrics(stats_path: Path, testcase_name: Optional[str] = None) -> Dict[str, Any]:
    """Extract useful metrics from a gem5 stats file.
    These values are later included in the JSON and HTML summaries.
    """
    if not stats_path.exists():
        return {"stats_path": str(stats_path), "present": False}

    content = stats_path.read_text(encoding="utf-8", errors="replace")
    metrics: Dict[str, Any] = {"stats_path": str(stats_path), "present": True}
    for key, pattern in STATS_METRIC_PATTERNS.items():
        match = pattern.search(content)
        if match:
            metrics[key] = _parse_stat_number(match.group(1))

    testcase_tag = str(testcase_name or "").strip()
    if testcase_tag in EXTRA_METRICS_TESTCASES:
        # Collect cache hierarchy metrics for clusters0..N when available.
        for metric_name, pattern in EXTRA_CLUSTER_METRIC_PATTERNS.items():
            for match in pattern.finditer(content):
                cluster = match.group("cluster")
                metrics[f"clusters{cluster}.{metric_name}"] = _parse_stat_number(match.group(2))

        # Collect per-core generator metrics and aggregated values for cores0/1/2/3.
        for metric_name in EXTRA_CORE_GENERATOR_METRICS:
            pattern = re.compile(
                rf"^board\.processor\.cores(?P<core>\d+)\.generator\.{re.escape(metric_name)}\s+([0-9.eE+-]+)",
                re.MULTILINE,
            )
            per_core_values: Dict[int, Any] = {}
            for match in pattern.finditer(content):
                core_idx = int(match.group("core"))
                value = _parse_stat_number(match.group(2))
                per_core_values[core_idx] = value
                metrics[f"board.processor.cores{core_idx}.generator.{metric_name}"] = value

            if per_core_values and all(isinstance(v, (int, float)) for v in per_core_values.values()):
                core_sum = float(sum(float(v) for v in per_core_values.values()))
                metrics[f"board.processor.cores0/1/2/3.generator.{metric_name}"] = core_sum
                metrics[f"board.processor.cores0_to_n.generator.{metric_name}.sum"] = core_sum
    return metrics


def analyze_compile_log(
    compile_log: Path, target: str, logger: SmokeLogger
) -> tuple[bool, Optional[str]]:
    """Inspect the compile log for failure patterns.
    It checks whether the build passed and whether the expected gem5 link step completed.
    """
    if not compile_log.exists():
        logger.error(f"Compile log was not created: {compile_log}")
        return False, "Compile log was not created"

    log_text = compile_log.read_text(encoding="utf-8", errors="replace")
    lower_text = log_text.lower()

    for pattern in COMPILE_ERROR_PATTERNS:
        if re.search(pattern, lower_text, flags=re.IGNORECASE):
            logger.error(
                f"Compile log matched known error pattern '{pattern}' for {target}: {compile_log}"
            )
            return False, f"Matched compile error pattern: {pattern}"

    link_pattern = rf"\[\s*LINK\]\s*->\s*ALL/{re.escape(target)}\b"
    if not re.search(link_pattern, log_text):
        logger.error(
            f"Compile log does not contain required link marker for {target}: {compile_log}"
        )
        return False, f"Missing link marker: [    LINK]  -> ALL/{target}"

    logger.warning(f"Compile log indicates PASS for {target}: {compile_log}")
    return True, f"Found link marker: [    LINK]  -> ALL/{target}"


def compile_gem5(
    repo_dir: Path,
    output_dir: Path,
    logger: SmokeLogger,
    build_type: str = "opt",
) -> tuple[Path, bool, Path, float, str]:
    """Compile gem5 into the shared smoke-build output directory.
    The result is copied into the run-specific build tree and logged for reporting.
    """
    results_dir = output_dir / "RESULTS"
    build_dir = output_dir / "build"
    build_dir.mkdir(parents=True, exist_ok=True)

    target = "gem5.opt" if build_type == "opt" else "gem5.debug"
    gem5_binary = build_dir / "ALL" / target
    fallback_binary = repo_dir / f"build/ALL/{target}"
    if not gem5_binary.exists() and fallback_binary.exists():
        gem5_binary = fallback_binary

    if should_skip_build(repo_dir, gem5_binary, logger):
        compile_log = output_dir / "RESULTS" / "compilation" / f"compile_{build_type}.log"
        compile_log.parent.mkdir(parents=True, exist_ok=True)
        skip_reason = "Build skipped because the existing binary is up to date."
        compile_log.write_text(f"{skip_reason}\n", encoding="utf-8")
        logger.warning("Skipping compile step because the binary is already present and source files are unchanged.")
        return gem5_binary, True, compile_log, 0.0, skip_reason

    logger.warning(f"Compiling gem5 ({build_type}) inside {repo_dir}")
    compile_log = output_dir / "RESULTS" / "compilation" / f"compile_{build_type}.log"
    compile_log.parent.mkdir(parents=True, exist_ok=True)
    compile_log.write_text(
        f"Build started for {build_type}\nWorking directory: {repo_dir}\n",
        encoding="utf-8",
    )
    compile_started = time.perf_counter()
    completed = run_command(
        [
            "scons",
            f"build/ALL/{target}",
            "-j20",
            "--ignore-style",
            "--install-hooks",
        ],
        cwd=repo_dir,
        logger=logger,
        allow_failure=True,
        log_file=compile_log,
        input_text="y\n",
    )

    if gem5_binary.exists():
        success = completed.returncode == 0
    else:
        fallback_binary = repo_dir / f"build/ALL/{target}"
        if fallback_binary.exists():
            gem5_binary = fallback_binary
            success = completed.returncode == 0
        else:
            success = False

    log_success, log_reason = analyze_compile_log(compile_log, target, logger)
    success = success and log_success

    if success and gem5_binary.exists():
        output_binary = output_dir / "build" / "ALL" / target
        output_binary.parent.mkdir(parents=True, exist_ok=True)
        if gem5_binary.resolve() != output_binary.resolve():
            shutil.copy2(gem5_binary, output_binary)
        gem5_binary = output_binary
    compile_runtime_seconds = round(time.perf_counter() - compile_started, 3)
    if not success:
        logger.error(f"Compilation failed. See log: {compile_log}")
        return gem5_binary, False, compile_log, compile_runtime_seconds, log_reason

    logger.warning(f"Compilation complete. Binary: {gem5_binary}")
    return gem5_binary, True, compile_log, compile_runtime_seconds, log_reason


def write_compilation_result(
    compile_dir: Path,
    chip_name: str,
    build_type: str,
    gem5_binary: Path,
    compile_log: Path,
    success: Optional[bool],
    reason: Optional[str],
    logger: SmokeLogger,
) -> None:
    """Write a per-chip compilation report to JSON.
    This records whether the build passed, where the binary lives, and the log path.
    """
    compile_dir.mkdir(parents=True, exist_ok=True)
    result_path = compile_dir / "results_compilation.json"
    log_copy_path = compile_dir / "compile.log"

    if compile_log.exists():
        log_copy_path.write_text(compile_log.read_text(encoding="utf-8"), encoding="utf-8")

    if success is None:
        status = "SKIP"
    elif success:
        status = "PASS"
    else:
        status = "FAIL"

    payload: Dict[str, Any] = {
        "chip": chip_name,
        "status": status,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "build_type": build_type,
        "binary_path": str(gem5_binary),
        "compile_directory": str(compile_dir),
        "log_file": str(log_copy_path),
        "result_file": str(result_path),
        "reason": reason,
    }

    result_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    logger.warning(f"Wrote compilation report: {result_path}")


def write_general_summary(
    output_dir: Path,
    logger: SmokeLogger,
    git_metadata: Dict[str, Any],
    build_type: str,
    skip_compilation: bool,
    compile_success: Optional[bool],
    gem5_binary: Path,
    compile_log: Path,
    compile_reason: Optional[str],
    chip_results: List[Dict[str, Any]],
    total_runtime_seconds: float,
    compilation_runtime_seconds: float,
    simulation_runtime_seconds: float,
) -> None:
    """Write the full run summary to JSON.
    It consolidates git, compile, simulation, and timing information in one file.
    """
    summary_path = output_dir / "RESULTS" / "general_results.json"
    chipwise_payload: Dict[str, Any] = {}
    total_testcases = 0

    def compact_testcase(entry: Dict[str, Any]) -> Dict[str, Any]:
        return {
            "compile_status": entry.get("compile_status"),
            "simulation_status": entry.get("simulation_status"),
            "output_dir": entry.get("output_dir"),
            "simulation_log": entry.get("simulation_log"),
            "return_code": entry.get("return_code"),
            "script": entry.get("script"),
            "runtime_seconds": entry.get("runtime_seconds", 0.0),
            "stats_metrics": entry.get("stats_metrics"),
            "compile_log": entry.get("compile_log"),
            "binary_path": entry.get("binary_path"),
            "compile_directory": entry.get("compile_directory"),
            "reason": entry.get("reason"),
        }

    for entry in chip_results:
        chip_name = entry.get("chip")
        case_name = entry.get("case") or entry.get("testcase_name") or "default"
        if chip_name:
            if chip_name not in chipwise_payload:
                chipwise_payload[chip_name] = {
                    "runtime_seconds": 0.0,
                    "pass_count": 0,
                    "fail_count": 0,
                    "skip_count": 0,
                    "testcases": {},
                }

            chip_bucket = chipwise_payload[chip_name]
            chip_bucket["testcases"][case_name] = compact_testcase(entry)
            chip_bucket["runtime_seconds"] += float(entry.get("runtime_seconds", 0.0) or 0.0)

            case_status = entry.get("simulation_status") or entry.get("status") or "SKIP"
            if case_status == "PASS":
                chip_bucket["pass_count"] += 1
            elif case_status == "FAIL":
                chip_bucket["fail_count"] += 1
            else:
                chip_bucket["skip_count"] += 1

    for chip_name, chip_bucket in chipwise_payload.items():
        chip_bucket["runtime_seconds"] = round(chip_bucket.get("runtime_seconds", 0.0), 3)
        chip_bucket["total_testcases"] = len(chip_bucket.get("testcases", {}))
        total_testcases += chip_bucket["total_testcases"]

    payload: Dict[str, Any] = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "output_dir": str(output_dir),
        "build_type": build_type,
        "skip_compilation": skip_compilation,
        "total_runtime_seconds": round(total_runtime_seconds, 3),
        "compilation_runtime_seconds": round(compilation_runtime_seconds, 3),
        "simulation_runtime_seconds": round(simulation_runtime_seconds, 3),
        "git_details": git_metadata,
        "compilation": {
            "status": "SKIP" if skip_compilation else ("PASS" if compile_success else "FAIL"),
            "success": None if skip_compilation else compile_success,
            "runtime_seconds": round(compilation_runtime_seconds, 3),
            "binary_path": str(gem5_binary),
            "log_file": str(compile_log),
            "build_type": build_type,
            "reason": compile_reason,
        },
        "simulation": {
            "runtime_seconds": round(simulation_runtime_seconds, 3),
            "chips": chipwise_payload,
            "total_chips": len(chipwise_payload),
            "total_testcases": total_testcases,
        },
    }
    summary_path.parent.mkdir(parents=True, exist_ok=True)
    summary_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    logger.warning(f"Wrote general summary: {summary_path}")


def update_history_results(output_dir: Path, logger: SmokeLogger) -> None:
    """Append the current run into the persistent history store.
    This keeps a growing JSON history of smoke results for later reporting.
    """
    history_dir = DEFAULT_HISTORY_DIR
    history_dir.mkdir(parents=True, exist_ok=True)
    history_path = history_dir / "history_results.json"
    general_results_path = output_dir / "RESULTS" / "general_results.json"

    if not general_results_path.exists():
        logger.warning(f"No general results found to add to history: {general_results_path}")
        return

    current_summary = json.loads(general_results_path.read_text(encoding="utf-8"))
    build_number = output_dir.name

    simulation_section = current_summary.get("simulation", {})
    simulation_chips = simulation_section.get("chips", {})

    total_testcases = 0
    total_pass = 0
    total_fail = 0
    total_skip = 0
    if isinstance(simulation_chips, dict):
        for chip_payload in simulation_chips.values():
            if not isinstance(chip_payload, dict):
                continue
            total_testcases += int(chip_payload.get("total_testcases", 0) or 0)
            total_pass += int(chip_payload.get("pass_count", 0) or 0)
            total_fail += int(chip_payload.get("fail_count", 0) or 0)
            total_skip += int(chip_payload.get("skip_count", 0) or 0)

    if history_path.exists():
        try:
            existing = json.loads(history_path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            existing = {}
    else:
        existing = {}

    if not isinstance(existing, dict):
        existing = {}

    runs = existing.get("runs")
    if not isinstance(runs, dict):
        runs = {}

    runs[build_number] = {
        "build_number": build_number,
        "output_dir": str(output_dir),
        "updated_at": datetime.now(timezone.utc).isoformat(),
        "summary": {
            "total_chips": int(simulation_section.get("total_chips", 0) or 0),
            "total_testcases": total_testcases,
            "pass_count": total_pass,
            "fail_count": total_fail,
            "skip_count": total_skip,
            "simulation_runtime_seconds": simulation_section.get("runtime_seconds"),
        },
        "general_results": current_summary,
    }

    existing["runs"] = runs
    existing["latest_build_number"] = build_number
    existing["latest_output_dir"] = str(output_dir)
    existing["updated_at"] = datetime.now(timezone.utc).isoformat()
    existing["total_runs"] = len(runs)

    history_path.write_text(json.dumps(existing, indent=2), encoding="utf-8")
    logger.warning(f"Updated history results: {history_path}")


def select_chips(
    chip_config: Dict[str, Any],
    chip_names: Optional[List[str]],
    logger: SmokeLogger,
) -> List[tuple[str, Dict[str, Any]]]:
    """Select the requested chip entries from the configuration.
    Passing ``ALL`` selects every chip entry from the configuration.
    """
    if not isinstance(chip_config, dict):
        return []

    # Accept both list-style argparse values and plain strings for resilience.
    raw_names: List[Any] = []
    if chip_names is None:
        raw_names = []
    elif isinstance(chip_names, str):
        raw_names = [chip_names]
    else:
        raw_names = list(chip_names)

    normalized_names: List[str] = []
    for raw_name in raw_names:
        for token in str(raw_name).split(","):
            cleaned = token.strip()
            if cleaned:
                normalized_names.append(cleaned)

    # No explicit chip names means "run all chips".
    if not normalized_names or any(name.upper() == "ALL" for name in normalized_names):
        selected_names = [name for name in chip_config.keys() if isinstance(chip_config[name], dict)]
        if not selected_names:
            logger.fatal("No chip entries were found in the chip configuration.")
            return []
        logger.warning(f"Selecting all chips from configuration: {selected_names}")
        return [(name, chip_config[name]) for name in selected_names]

    selected: List[tuple[str, Dict[str, Any]]] = []
    for chip_name in normalized_names:
        if chip_name in chip_config:
            selected.append((chip_name, chip_config[chip_name]))
        else:
            logger.fatal(f"Chip '{chip_name}' was not found in the chip configuration.")
    return selected


def expand_simulation_cases(chip_config: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Expand the chip configuration into individual simulation cases.
    Each named test becomes one runnable case for the workflow.
    """
    simulate_config = chip_config.get("simulate", {})
    if not isinstance(simulate_config, dict):
        return [{"name": "default", "config": {}}]

    named_cases = simulate_config.get("tests")
    if isinstance(named_cases, dict) and named_cases:
        cases = []
        for case_name, case_config in named_cases.items():
            if isinstance(case_config, dict):
                merged_case = dict(simulate_config)
                merged_case.pop("tests", None)
                merged_case.update(case_config)
                merged_case.setdefault("case_name", case_name)
                merged_case.setdefault("category", case_name)
                cases.append({"name": case_name, "config": merged_case})
        return cases or [{"name": "default", "config": simulate_config}]

    return [{"name": "default", "config": simulate_config}]


def build_simulation_command(
    repo_dir: Path,
    gem5_binary: Path,
    chip_name: str,
    chip_config: Dict[str, Any],
    case_name: str,
) -> List[str]:
    """Build a gem5 command line for one simulation case.
    It assembles the binary, script path, and output directory arguments for the run.
    """
    command: List[str] = [str(gem5_binary)]
    command.extend(chip_config.get("gem5_args", []))

    default_script = repo_dir / "configs/example/se.py"
    script_path: Optional[Path] = None
    if chip_config.get("sim_script"):
        script_path = Path(chip_config["sim_script"]).expanduser()
        if not script_path.is_absolute():
            script_path = repo_dir / script_path
        command.append(str(script_path))
    elif default_script.exists():
        script_path = default_script
        command.append(str(script_path))

    sim_script_args = list(chip_config.get("sim_script_args", []))

    cleaned_args: List[str] = []
    skip_next = False
    for index, token in enumerate(sim_script_args):
        if skip_next:
            skip_next = False
            continue
        if token == "--outdir":
            skip_next = True
            continue
        if str(token).startswith("--outdir="):
            continue
        cleaned_args.append(token)

    outdir = chip_config.get("outdir")
    if not outdir:
        outdir = f"{chip_name}_{case_name}"
    if not str(outdir).startswith("/"):
        outdir = str(repo_dir / "RESULTS" / "simulation" / chip_name / case_name / str(outdir))
    cleaned_args.extend([f"--outdir={outdir}"])

    command.extend(cleaned_args)
    return command


def build_compile_command(repo_dir: Path, build_type: str) -> List[str]:
    """Build the compile command for the requested gem5 build type.
    This is used by the dry-run mode to show the command that would be executed.
    """
    target = "gem5.opt" if build_type == "opt" else "gem5.debug"
    return [
        "scons",
        f"build/ALL/{target}",
        "-j20",
        "--ignore-style",
        "--install-hooks",
    ]


def write_dry_run_summary(
    output_dir: Path,
    logger: SmokeLogger,
    chip_config: Dict[str, Any],
    build_type: str,
    planned_compile_command: List[str],
    planned_simulation_commands: List[Dict[str, Any]],
) -> None:
    """Write the planned command list for a dry run.
    This makes the workflow easier to inspect before any real build or simulation starts.
    """
    summary_path = output_dir / "RESULTS" / "dry_run_results.json"
    payload = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "output_dir": str(output_dir),
        "build_type": build_type,
        "mode": "dry_run",
        "chip_configuration_keys": list(chip_config.keys()) if isinstance(chip_config, dict) else [],
        "binary_path": str(output_dir / "build" / "ALL" / ("gem5.opt" if build_type == "opt" else "gem5.debug")),
        "results_root": str(output_dir / "RESULTS"),
        "compile_command": planned_compile_command,
        "simulation_commands": planned_simulation_commands,
    }
    summary_path.parent.mkdir(parents=True, exist_ok=True)
    summary_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    logger.warning(f"Wrote dry-run summary: {summary_path}")


def simulate_gem5(
    repo_dir: Path,
    output_dir: Path,
    gem5_binary: Path,
    logger: SmokeLogger,
    chip_name: str,
    chip_config: Dict[str, Any],
    case_name: Optional[str] = None,
) -> Dict[str, Any]:
    """Run one chip simulation case and capture its results.
    The outputs are written under the chip-specific results directory for reporting.
    """
    case_name = case_name or chip_config.get("case_name", "default")
    chip_dir = output_dir / "RESULTS" / "simulation" / chip_name / case_name
    chip_dir.mkdir(parents=True, exist_ok=True)

    script_path: Optional[Path] = None
    if chip_config.get("sim_script"):
        candidate = Path(str(chip_config["sim_script"])).expanduser()
        script_path = candidate if candidate.is_absolute() else (repo_dir / candidate)
    else:
        default_script = repo_dir / "configs/example/se.py"
        if default_script.exists():
            script_path = default_script

    if script_path is None or not script_path.exists():
        logger.warning(
            f"No simulation script was found for {chip_name}/{case_name}; skipping simulation"
        )
        return {
            "chip": chip_name,
            "status": "SKIP",
            "reason": "No simulation script available",
            "output_dir": str(chip_dir),
            "command": [],
        }

    case_outdir = chip_config.get("outdir") or case_name
    if not str(case_outdir).startswith("/"):
        resolved_outdir = output_dir / "RESULTS" / "simulation" / chip_name / str(case_outdir)
    else:
        resolved_outdir = Path(str(case_outdir))
    resolved_outdir.mkdir(parents=True, exist_ok=True)

    # Build script args from chip configuration and remove args that should be
    # handled at the gem5 level or are not consumed by these materials scripts.
    raw_script_args = [str(token) for token in chip_config.get("sim_script_args", [])]
    script_args: List[str] = []
    skip_next = False
    workload_stripped = False
    for token in raw_script_args:
        if skip_next:
            skip_next = False
            continue
        if token == "--outdir":
            skip_next = True
            continue
        if token.startswith("--outdir="):
            continue
        if token == "--workload":
            skip_next = True
            workload_stripped = True
            continue
        if token.startswith("--workload="):
            workload_stripped = True
            continue
        script_args.append(token)

    if workload_stripped:
        logger.warning(
            f"Ignoring --workload for {chip_name}/{case_name}; script does not consume this argument."
        )

    command: List[str] = [
        str(gem5_binary),
        *[str(arg) for arg in chip_config.get("gem5_args", [])],
        f"--outdir={resolved_outdir}",
        "--redirect-stdout",
        "--redirect-stderr",
        str(script_path),
        *script_args,
    ]

    simulation_log = resolved_outdir / "simulation.log"
    logger.warning(
        f"Running simulation for {chip_name}/{case_name} with: {' '.join(command)}"
    )
    simulation_started = time.perf_counter()
    completed = run_command(command, cwd=repo_dir, logger=logger, allow_failure=True, log_file=simulation_log)
    simulation_runtime_seconds = round(time.perf_counter() - simulation_started, 3)
    stats_metrics = read_stats_metrics(resolved_outdir / "stats.txt", testcase_name=case_name)
    return {
        "chip": chip_name,
        "testcase_name": case_name,
        "status": "PASS" if completed.returncode == 0 else "FAIL",
        "return_code": completed.returncode,
        "command": command,
        "output_dir": str(resolved_outdir),
        "simulation_log": str(simulation_log),
        "script": str(script_path),
        "runtime_seconds": simulation_runtime_seconds,
        "stats_metrics": stats_metrics,
    }


def main() -> int:
    """Coordinate the full smoke workflow.
    This is the entry point that parses options, builds, runs, and reports the results.
    """
    args = parse_args()
    logger = SmokeLogger(verbose=args.verbose)

    start_time = time.perf_counter()

    input_dir = Path(args.input_dir).expanduser().resolve()
    output_dir = resolve_output_dir(input_dir, args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    logger.warning(f"Input directory: {input_dir}")
    logger.warning(f"Output directory: {output_dir}")

    chip_config = load_chip_configuration(args.chip_configuration, logger)

    if args.dry_run:
        repo_dir = output_dir
        planned_compile_command = build_compile_command(repo_dir, args.compile)
        planned_simulation_commands: List[Dict[str, Any]] = []
        if isinstance(chip_config, dict):
            selected_chips = select_chips(chip_config, args.chip_name, logger)
            for chip_name, chip_values in selected_chips:
                if not isinstance(chip_values, dict):
                    continue
                for case in expand_simulation_cases(chip_values):
                    case_name = case["name"]
                    case_config = case["config"]
                    case_outdir = case_config.get("outdir") or case_name
                    if not str(case_outdir).startswith("/"):
                        resolved_outdir = output_dir / "RESULTS" / "simulation" / chip_name / case_name
                    else:
                        resolved_outdir = Path(str(case_outdir))
                    simulated_binary = output_dir / "build" / "ALL" / ("gem5.opt" if args.compile == "opt" else "gem5.debug")
                    planned_simulation_commands.append(
                        {
                            "chip": chip_name,
                            "case": case_name,
                            "command": build_simulation_command(repo_dir, simulated_binary, chip_name, case_config, case_name),
                            "resolved_outdir": str(resolved_outdir),
                            "output_dir": str(resolved_outdir),
                            "script": case_config.get("sim_script"),
                            "binary_path": str(simulated_binary),
                        }
                    )

        logger.warning("Dry run enabled; no commands will be executed.")
        logger.warning(f"Planned compile command: {' '.join(planned_compile_command)}")
        for entry in planned_simulation_commands:
            logger.warning(
                f"Planned simulation for {entry['chip']}/{entry['case']}: {' '.join(entry['command'])}"
            )
        write_dry_run_summary(
            output_dir,
            logger,
            chip_config,
            args.compile,
            planned_compile_command,
            planned_simulation_commands,
        )
        return 0

    repo_dir = output_dir
    git_metadata = git_clone(DEFAULT_REPO_URL, repo_dir, args.branch, logger)
    logger.debug(f"Git metadata captured: {git_metadata}")

    results_dir = output_dir / "RESULTS"
    (results_dir / "compilation").mkdir(parents=True, exist_ok=True)
    (results_dir / "simulation").mkdir(parents=True, exist_ok=True)

    if args.skip_compilation:
        logger.warning("Skipping compilation step as requested.")
        compile_log = results_dir / "compilation" / f"compile_{args.compile}.log"
        compile_log.parent.mkdir(parents=True, exist_ok=True)
        compile_reason = f"Compilation skipped by user for build type {args.compile}."
        compile_log.write_text(f"{compile_reason}\n", encoding="utf-8")
        gem5_binary = output_dir / "build" / "ALL" / ("gem5.opt" if args.compile == "opt" else "gem5.debug")
        compile_success = None
        compile_runtime_seconds = 0.0
    else:
        gem5_binary, compile_success, compile_log, compile_runtime_seconds, compile_reason = compile_gem5(repo_dir, output_dir, logger, build_type=args.compile)

    chip_results: List[Dict[str, Any]] = []
    simulation_runtime_seconds = 0.0
    if isinstance(chip_config, dict):
        selected_chips = select_chips(chip_config, args.chip_name, logger)
        for chip_name, chip_values in selected_chips:
            if not isinstance(chip_values, dict):
                continue
            compile_dir = results_dir / "compilation" / chip_name
            compile_dir.mkdir(parents=True, exist_ok=True)
            logger.warning(f"Preparing compile directory for {chip_name}: {compile_dir}")
            if args.skip_compilation:
                write_compilation_result(
                    compile_dir,
                    chip_name,
                    args.compile,
                    gem5_binary,
                    compile_log,
                    None,
                    compile_reason,
                    logger,
                )
                simulation_cases = expand_simulation_cases(chip_values)
                logger.warning(f"Skipping simulation for {chip_name} because compilation was disabled.")
                for case in simulation_cases:
                    case_name = case["name"]
                    case_config = case["config"]
                    case_outdir = case_config.get("outdir") or case_name
                    if not str(case_outdir).startswith("/"):
                        resolved_outdir = output_dir / "RESULTS" / "simulation" / chip_name / case_name
                    else:
                        resolved_outdir = Path(str(case_outdir))
                    chip_results.append(
                        {
                            "chip": chip_name,
                            "case": case_name,
                            "status": "SKIP",
                            "compile_status": "SKIP",
                            "simulation_status": "SKIP",
                            "reason": "Compilation disabled",
                            "output_dir": str(resolved_outdir),
                            "runtime_seconds": 0.0,
                            "compile_log": str(compile_log),
                            "binary_path": str(gem5_binary),
                            "compile_directory": str(compile_dir),
                        }
                    )
                continue

            if not compile_success or not gem5_binary.exists():
                logger.error(f"Skipping simulation for {chip_name} because no gem5 binary was produced.")
                write_compilation_result(
                    compile_dir,
                    chip_name,
                    args.compile,
                    gem5_binary,
                    compile_log,
                    False,
                    compile_reason,
                    logger,
                )
                chip_results.append(
                    {
                        "chip": chip_name,
                        "status": "SKIP",
                        "compile_status": "FAIL",
                        "simulation_status": "SKIP",
                        "reason": "No gem5 binary produced",
                        "output_dir": str(output_dir / "simulation" / chip_name),
                        "runtime_seconds": 0.0,
                        "compile_log": str(compile_log),
                        "binary_path": str(gem5_binary),
                        "compile_directory": str(compile_dir),
                    }
                )
                continue

            write_compilation_result(
                compile_dir,
                chip_name,
                args.compile,
                gem5_binary,
                compile_log,
                compile_success,
                compile_reason,
                logger,
            )
            simulation_cases = expand_simulation_cases(chip_values)
            if args.skip_simulation:
                logger.warning(f"Skipping simulation for {chip_name} because --skip_simulation was requested.")
                for case in simulation_cases:
                    case_name = case["name"]
                    case_config = case["config"]
                    case_outdir = case_config.get("outdir") or case_name
                    if not str(case_outdir).startswith("/"):
                        resolved_outdir = output_dir / "RESULTS" / "simulation" / chip_name / case_name
                    else:
                        resolved_outdir = Path(str(case_outdir))
                    chip_results.append(
                        {
                            "chip": chip_name,
                            "case": case_name,
                            "status": "SKIP",
                            "compile_status": "PASS" if compile_success else "FAIL",
                            "simulation_status": "SKIP",
                            "output_dir": str(resolved_outdir),
                            "simulation_log": "N/A",
                            "return_code": "N/A",
                            "script": case_config.get("sim_script"),
                            "runtime_seconds": 0.0,
                            "stats_metrics": {"present": False},
                            "compile_log": str(compile_log),
                            "binary_path": str(gem5_binary),
                            "compile_directory": str(compile_dir),
                            "reason": "Simulation skipped by user",
                        }
                    )
                continue
            for case in simulation_cases:
                case_name = case["name"]
                case_config = case["config"]
                case_dir = output_dir / "RESULTS" / "simulation" / chip_name / case_name
                case_dir.mkdir(parents=True, exist_ok=True)
                simulation_result = simulate_gem5(
                    repo_dir,
                    output_dir,
                    gem5_binary,
                    logger,
                    chip_name,
                    case_config,
                    case_name=case_name,
                )
                simulation_runtime_seconds += simulation_result.get("runtime_seconds", 0.0)
                chip_results.append(
                    {
                        "chip": chip_name,
                        "case": case_name,
                        "status": simulation_result["status"],
                        "compile_status": "PASS" if compile_success else "FAIL",
                        "simulation_status": simulation_result["status"],
                        "output_dir": simulation_result.get("output_dir"),
                        "simulation_log": simulation_result.get("simulation_log"),
                        "return_code": simulation_result.get("return_code"),
                        "script": simulation_result.get("script"),
                        "runtime_seconds": simulation_result.get("runtime_seconds", 0.0),
                        "stats_metrics": simulation_result.get("stats_metrics"),
                        "compile_log": str(compile_log),
                        "binary_path": str(gem5_binary),
                        "compile_directory": str(compile_dir),
                    }
                )
    else:
        logger.warning("Chip configuration was not a dictionary; no per-chip simulation was run.")

    total_runtime_seconds = time.perf_counter() - start_time
    write_general_summary(
        output_dir,
        logger,
        git_metadata,
        args.compile,
        args.skip_compilation,
        compile_success if "compile_success" in locals() else None,
        gem5_binary if "gem5_binary" in locals() else output_dir / "build" / "ALL" / ("gem5.opt" if args.compile == "opt" else "gem5.debug"),
        compile_log if "compile_log" in locals() else output_dir / "compilation" / f"compile_{args.compile}.log",
        compile_reason if "compile_reason" in locals() else None,
        chip_results,
        total_runtime_seconds,
        compile_runtime_seconds if "compile_runtime_seconds" in locals() else 0.0,
        simulation_runtime_seconds,
    )

    update_history_results(output_dir, logger)

    if args.lsf == 1:
        logger.warning("LSF mode requested; submitting the workflow via bsub.")
        submission_command = build_lsf_submission_command(args, output_dir, logger)
        logger.warning(f"Submitting LSF command: {' '.join(submission_command)}")
        completed = run_command(submission_command, cwd=repo_dir, logger=logger, allow_failure=True)
        if completed.returncode == 0:
            logger.warning("LSF job submitted successfully.")
        else:
            logger.error("LSF submission failed.")
        return 0

    logger.warning("Smoke workflow completed successfully.")
    generate_weekly_results_html(output_dir, logger)
    generate_weekly_results_json(output_dir, logger)
    generate_jenkins_history_weekly_results_html(DEFAULT_HISTORY_DIR, logger, limit=30)
    generate_jenkins_history_weekly_results_json(DEFAULT_HISTORY_DIR, logger, limit=30)

    comparison_script = Path(__file__).resolve().parents[1] / "compare_golden_results.py"
    comparison_report_dir = output_dir / "RESULTS" / "golden_comparison"
    comparison = run_command(
        [
            sys.executable,
            str(comparison_script),
            "--build-dir",
            str(output_dir),
            "--golden-dir",
            str(DEFAULT_GOLDEN_DIR),
            "--report-dir",
            str(comparison_report_dir),
        ],
        cwd=output_dir,
        logger=logger,
        allow_failure=True,
    )
    logger.warning(
        f"Golden comparison completed with exit code {comparison.returncode}: {comparison_report_dir}"
    )

    if args.send_email:
        history_report_path = DEFAULT_HISTORY_DIR / "jenkins_history_weekly_results.html"
        email_sent = send_history_report_email(
            html_report_path=history_report_path,
            to_addresses=args.recipient_email or ["shreyassbagi@gmail.com"],
            smtp_server=args.smtp_server,
            smtp_port=args.smtp_port,
            sender_email=args.sender_email,
            sender_password=args.sender_password,
            subject=args.email_subject,
        )
        if email_sent:
            logger.warning(f"Email sent successfully with attachment: {history_report_path}")
        else:
            logger.warning(
                "Email delivery was not completed. Check SMTP settings, credentials, or recipient configuration."
            )

    return 0


if __name__ == "__main__":
    sys.exit(main())

