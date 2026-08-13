#!/usr/bin/env python3
"""Compare a completed gem5 build against per-chip GOLDEN metric baselines."""

from __future__ import annotations

import argparse
import csv
import html
import json
import re
from pathlib import Path
from typing import Any, Dict, Iterable, List, Tuple

DEFAULT_TOLERANCE_PERCENT = 5.0
NUMBER_PATTERN = r"[-+]?(?:\d+(?:\.\d*)?|\.\d+)(?:[eE][-+]?\d+)?"
BASE_METRIC_NAMES = {
    "simSeconds",
    "simTicks",
    "finalTick",
    "simFreq",
    "hostSeconds",
    "hostTickRate",
    "hostMemory",
}


def _number(value: str) -> int | float | None:
    try:
        parsed = float(value)
    except ValueError:
        return None
    return int(parsed) if parsed.is_integer() else parsed


def _flatten_numeric_values(value: Any, prefix: str = "") -> Dict[str, float]:
    flattened: Dict[str, float] = {}
    if isinstance(value, dict):
        for key, child in value.items():
            child_prefix = f"{prefix}.{key}" if prefix else str(key)
            flattened.update(_flatten_numeric_values(child, child_prefix))
    elif isinstance(value, (int, float)) and not isinstance(value, bool):
        flattened[prefix] = float(value)
    return flattened


def _metric_aliases(key: str) -> Iterable[str]:
    yield key
    if key.startswith("board.cache_hierarchy."):
        yield key[len("board.cache_hierarchy.") :]
    if key.startswith("board.processor."):
        yield key[len("board.processor.") :]


def parse_stats(stats_path: Path) -> Dict[str, float]:
    if not stats_path.exists():
        return {}
    content = stats_path.read_text(encoding="utf-8", errors="replace")
    values: Dict[str, float] = {}
    for line in content.splitlines():
        match = re.match(rf"^\s*(\S+)\s+({NUMBER_PATTERN})(?:\s|$)", line)
        if not match:
            continue
        key, raw_value = match.groups()
        parsed = _number(raw_value)
        if parsed is None:
            continue
        for alias in _metric_aliases(key):
            values[alias] = float(parsed)

    for metric in ("numPackets", "numRetries", "totalReads", "totalWrites", "readBW", "writeBW"):
        core_values = [
            values[key]
            for key in values
            if re.fullmatch(rf"board\.processor\.cores\d+\.generator\.{re.escape(metric)}", key)
        ]
        if core_values:
            total = sum(core_values)
            values[f"board.processor.cores0/1/2/3.generator.{metric}"] = total
            values[f"board.processor.cores0_to_n.generator.{metric}.sum"] = total
    return values


def _load_golden(golden_file: Path) -> Tuple[Dict[str, Dict[str, float]], float]:
    payload = json.loads(golden_file.read_text(encoding="utf-8"))
    tolerance = float(payload.get("golden_profile", {}).get("tolerance_percent", DEFAULT_TOLERANCE_PERCENT))
    baselines = payload.get("golden_values", {})
    if not isinstance(baselines, dict):
        return {}, tolerance
    result: Dict[str, Dict[str, float]] = {}
    for testcase, values in baselines.items():
        if isinstance(values, dict):
            result[str(testcase)] = _flatten_numeric_values(values)
    return result, tolerance


def compare_build(build_dir: Path, golden_dir: Path, report_dir: Path | None = None) -> Dict[str, Any]:
    report_dir = report_dir or build_dir / "RESULTS" / "golden_comparison"
    report_dir.mkdir(parents=True, exist_ok=True)
    rows: List[Dict[str, Any]] = []

    for golden_file in sorted(golden_dir.glob("CHIP_*.json")):
        chip_name = golden_file.stem
        baselines, tolerance = _load_golden(golden_file)
        for testcase, golden_metrics in baselines.items():
            stats_path = build_dir / "RESULTS" / "simulation" / chip_name / testcase / "stats.txt"
            actual_metrics = parse_stats(stats_path)
            for metric, golden_value in sorted(golden_metrics.items()):
                actual_value = next((actual_metrics[alias] for alias in _metric_aliases(metric) if alias in actual_metrics), None)
                if actual_value is None:
                    status = "MISSING_ACTUAL"
                    deviation = None
                elif golden_value == 0:
                    deviation = 0.0 if actual_value == 0 else None
                    status = "PASS" if actual_value == 0 else "FAIL"
                else:
                    deviation = ((actual_value - golden_value) / abs(golden_value)) * 100.0
                    status = "PASS" if abs(deviation) <= tolerance else "FAIL"
                rows.append({
                    "chip_name": chip_name,
                    "testcase": testcase,
                    "metric": metric,
                    "stats_file": str(stats_path),
                    "golden_value": golden_value,
                    "actual_value": actual_value,
                    "deviation_percent": round(deviation, 4) if deviation is not None else None,
                    "tolerance_percent": tolerance,
                    "status": status,
                })

        if not baselines:
            rows.append({
                "chip_name": chip_name,
                "testcase": "*",
                "metric": "*",
                "stats_file": "",
                "golden_value": None,
                "actual_value": None,
                "deviation_percent": None,
                "tolerance_percent": tolerance,
                "status": "NO_BASELINE",
            })

    summary = {
        "build_dir": str(build_dir),
        "golden_dir": str(golden_dir),
        "tolerance_percent": DEFAULT_TOLERANCE_PERCENT,
        "total_rows": len(rows),
        "pass_count": sum(row["status"] == "PASS" for row in rows),
        "fail_count": sum(row["status"] == "FAIL" for row in rows),
        "missing_actual_count": sum(row["status"] == "MISSING_ACTUAL" for row in rows),
        "no_baseline_count": sum(row["status"] == "NO_BASELINE" for row in rows),
        "rows": rows,
        "note": "A 5% tolerance is applied to numeric metrics. NO_BASELINE is reported until golden_values are populated.",
    }
    (report_dir / "golden_comparison.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
    fieldnames = ["chip_name", "testcase", "metric", "golden_value", "actual_value", "deviation_percent", "tolerance_percent", "status", "stats_file"]
    with (report_dir / "golden_comparison.csv").open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)

    html_rows = "".join(
        "<tr class='status-{status}'><td>{chip}</td><td>{testcase}</td><td>{metric}</td><td>{golden}</td><td>{actual}</td><td>{deviation}</td><td>{tolerance}</td><td>{status}</td></tr>".format(
            status=html.escape(str(row["status"]).lower()),
            chip=html.escape(str(row["chip_name"])),
            testcase=html.escape(str(row["testcase"])),
            metric=html.escape(str(row["metric"])),
            golden=html.escape(str(row["golden_value"])),
            actual=html.escape(str(row["actual_value"])),
            deviation=html.escape(str(row["deviation_percent"])),
            tolerance=html.escape(str(row["tolerance_percent"])),
        )
        for row in rows
    )
    html_text = f"""<!doctype html><html><head><meta charset='utf-8'><title>Golden Comparison</title><style>body{{font-family:Arial,sans-serif;margin:24px;color:#14213d}}table{{border-collapse:collapse;width:100%}}th,td{{border:1px solid #dbe3ee;padding:8px;text-align:left;font-size:12px}}th{{background:#1f3a5f;color:white}}.status-pass{{background:#d9f2c2}}.status-fail{{background:#ffd6d6}}.status-missing_actual,.status-no_baseline{{background:#fff0c2}}</style></head><body><h1>Golden Comparison</h1><p>Build: {html.escape(str(build_dir))}<br>Golden: {html.escape(str(golden_dir))}<br>Allowed deviation: {DEFAULT_TOLERANCE_PERCENT}%</p><table><thead><tr><th>Chip</th><th>Testcase</th><th>Metric</th><th>Golden</th><th>Actual</th><th>Deviation %</th><th>Tolerance %</th><th>Status</th></tr></thead><tbody>{html_rows}</tbody></table></body></html>"""
    (report_dir / "golden_comparison.html").write_text(html_text, encoding="utf-8")
    return summary


def main() -> int:
    parser = argparse.ArgumentParser(description="Compare a gem5 build against per-chip GOLDEN baselines.")
    parser.add_argument("--build-dir", required=True, type=Path)
    parser.add_argument("--golden-dir", required=True, type=Path)
    parser.add_argument("--report-dir", type=Path)
    parser.add_argument("--fail-on-deviation", action="store_true")
    args = parser.parse_args()
    summary = compare_build(args.build_dir, args.golden_dir, args.report_dir)
    print(json.dumps({key: summary[key] for key in ("total_rows", "pass_count", "fail_count", "missing_actual_count", "no_baseline_count")}, indent=2))
    return 1 if args.fail_on_deviation and (summary["fail_count"] or summary["missing_actual_count"] or summary["no_baseline_count"]) else 0


if __name__ == "__main__":
    raise SystemExit(main())
