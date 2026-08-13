#!/usr/bin/env python3
"""HTML reporting helpers for the gem5 smoke workflow."""

from __future__ import annotations

import json
from datetime import datetime
from html import escape
from pathlib import Path
from typing import Any, Dict, List, Optional

# External CSS filename written alongside every HTML report to bypass Jenkins CSP.
_REPORT_CSS_FILENAME = "smoke_report.css"
_REPORT_CSS = """:root {
  color-scheme: light;
  --bg: #f6f8fb;
  --panel: #ffffff;
  --border: #dbe3ee;
  --heading: #14213d;
  --muted: #667085;
  --accent: #1f3a5f;
  --ok: #137333;
  --fail: #b42318;
  --skip: #7a4e00;
}
body {
  margin: 0;
  background: linear-gradient(180deg, #eef3f8 0%, var(--bg) 160px);
  color: var(--heading);
  font-family: Arial, Helvetica, sans-serif;
}
.page { max-width: 1600px; margin: 0 auto; padding: 24px; }
.hero {
  background: var(--panel);
  border: 1px solid var(--border);
  border-radius: 16px;
  padding: 20px 22px;
  box-shadow: 0 6px 24px rgba(15, 23, 42, 0.06);
  margin-bottom: 18px;
}
.hero h1 { margin: 0 0 6px 0; font-size: 28px; }
.hero p { margin: 0; color: var(--muted); line-height: 1.5; }
.section-title { font-size: 18px; margin: 20px 0 10px; }
.detail-panel {
  background: var(--panel);
  border: 1px solid var(--border);
  border-radius: 16px;
  padding: 18px 20px;
  box-shadow: 0 6px 24px rgba(15, 23, 42, 0.05);
}
.detail-line {
  display: grid;
  grid-template-columns: 220px 1fr;
  gap: 12px;
  padding: 7px 0;
  border-bottom: 1px solid #eef2f7;
}
.detail-line:last-child { border-bottom: 0; }
.detail-label {
  font-size: 12px;
  text-transform: uppercase;
  letter-spacing: 0.08em;
  color: var(--muted);
}
.detail-value { font-size: 14px; line-height: 1.45; word-break: break-word; }
.table-wrap {
  overflow: auto;
  border: 1px solid var(--border);
  border-radius: 16px;
  background: var(--panel);
  box-shadow: 0 6px 24px rgba(15, 23, 42, 0.05);
}
table { width: 100%; min-width: 1600px; border-collapse: collapse; background: var(--panel); }
th, td {
  padding: 10px 12px;
  border-bottom: 1px solid #e7edf5;
  vertical-align: top;
  text-align: left;
  font-size: 12px;
  word-break: break-word;
}
thead th {
  position: sticky;
  top: 0;
  background: var(--accent);
  color: #ffffff;
  z-index: 1;
  white-space: nowrap;
}
thead tr:nth-child(2) th { top: 39px; background: #27496d; }
tr:nth-child(even) td { background: #f9fbfd; }
td.group-cell { background: #f2f6fb; font-weight: 700; }
.status-pass { background: #92d050; color: #111111; font-weight: 700; }
.status-fail { background: #ff1a1a; color: #111111; font-weight: 700; }
.status-skip { background: #ffd966; color: #111111; font-weight: 700; }
.mono { font-family: SFMono-Regular, Menlo, Monaco, Consolas, monospace; font-size: 11px; white-space: pre-wrap; }
.small { color: var(--muted); font-size: 12px; margin-top: 8px; }
"""


__all__ = [
    "generate_jenkins_history_weekly_results_html",
    "generate_jenkins_history_weekly_results_json",
    "generate_weekly_results_html",
    "generate_weekly_results_json",
    "render_weekly_results_html",
]


def _parse_iso_timestamp(value: Optional[str]) -> float:
    """Convert an ISO timestamp into a sortable floating-point value.
    This helps the report logic order runs chronologically.
    """
    if not value:
        return 0.0
    try:
        return datetime.fromisoformat(value).timestamp()
    except ValueError:
        return 0.0


def _extract_stats_value(stats_metrics: Any, key: str) -> str:
    """Return a stats metric as a display-friendly string.
    Missing values are rendered as N/A so the report stays readable.
    """
    if not isinstance(stats_metrics, dict) or not stats_metrics.get("present"):
        return "N/A"
    value = stats_metrics.get(key)
    if value is None or value == "":
        return "N/A"
    return str(value)


def _group_report_rows(rows: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Group flat report rows by build and chip.
    This prepares the data for HTML tables that use row spans for compact display.
    """
    grouped_rows: List[Dict[str, Any]] = []
    current_group: Optional[Dict[str, Any]] = None
    current_key: Optional[tuple] = None

    for row in rows:
        key = (row.get("build_number", "N/A"), row.get("chip_name", "N/A"))
        if key != current_key:
            current_group = {
                "build_number": row.get("build_number", "N/A"),
                "chip_name": row.get("chip_name", "N/A"),
                "rows": [],
            }
            grouped_rows.append(current_group)
            current_key = key
        if current_group is not None:
            current_group["rows"].append(row)

    return grouped_rows


def _collect_report_rows(summary: Dict[str, Any], build_number: str) -> List[Dict[str, Any]]:
    """Flatten a smoke summary into per-chip and per-case report rows.
    These rows are consumed by the HTML renderer to produce the final table.
    """
    git_details = summary.get("git_details", {}) if isinstance(summary, dict) else {}
    compilation = summary.get("compilation", {}) if isinstance(summary, dict) else {}
    simulation = summary.get("simulation", {}) if isinstance(summary, dict) else {}
    chips = simulation.get("chips", {}) if isinstance(simulation, dict) else {}
    run_timestamp = summary.get("timestamp") or summary.get("updated_at") or ""
    git_files_change = git_details.get("changed_files", [])
    git_files_change_text = (
        "<br>".join(escape(str(item)) for item in git_files_change)
        if isinstance(git_files_change, list) and git_files_change
        else "N/A"
    )

    rows: List[Dict[str, Any]] = []
    if not isinstance(chips, dict):
        return rows

    for chip_name, chip_payload in chips.items():
        if not isinstance(chip_payload, dict):
            continue
        testcase_map = chip_payload.get("testcases", {})
        if not isinstance(testcase_map, dict) or not testcase_map:
            rows.append(
                {
                    "date": run_timestamp,
                    "build_number": build_number,
                    "chip_name": chip_name,
                    "case_name": "default",
                    "date": run_timestamp,
                    "commit_id": git_details.get("commit_id", "N/A"),
                    "commit_message": git_details.get("commit_message", "N/A"),
                    "username": git_details.get("pushed_by", "N/A"),
                    "compilation_result": compilation.get("status", "N/A"),
                    "compilation_run_time": compilation.get("runtime_seconds", 0.0),
                    "simulation_result": chip_payload.get("simulation_status", chip_payload.get("status", "N/A")),
                    "simulation_run_time": chip_payload.get("runtime_seconds", 0.0),
                    "sim_seconds": "N/A",
                    "host_seconds": "N/A",
                    "reason": chip_payload.get("reason", compilation.get("reason", "")),
                    "git_files_change": git_files_change_text,
                }
            )
            continue

        for case_name, testcase in testcase_map.items():
            if not isinstance(testcase, dict):
                continue
            rows.append(
                {
                    "date": run_timestamp,
                    "build_number": build_number,
                    "chip_name": chip_name,
                    "case_name": case_name,
                    "commit_id": git_details.get("commit_id", "N/A"),
                    "commit_message": git_details.get("commit_message", "N/A"),
                  "username": git_details.get("pushed_by", "N/A"),
                    "compilation_result": testcase.get("compile_status", compilation.get("status", "N/A")),
                    "compilation_run_time": compilation.get("runtime_seconds", 0.0),
                    "simulation_result": testcase.get("simulation_status", testcase.get("status", "N/A")),
                    "simulation_run_time": testcase.get("runtime_seconds", 0.0),
                    "sim_seconds": _extract_stats_value(testcase.get("stats_metrics"), "simSeconds"),
                    "host_seconds": _extract_stats_value(testcase.get("stats_metrics"), "hostSeconds"),
                    "reason": testcase.get("reason", compilation.get("reason", "")),
                    "git_files_change": git_files_change_text,
                }
            )

    return rows


def render_weekly_results_html(page_title: str, summary_fields: Dict[str, Any], rows: List[Dict[str, Any]]) -> str:
  """Render the smoke report HTML page.
  It creates the summary details panel and the grouped table used for the report.
  """

  def cell(value: Any) -> str:
    text = "" if value is None else str(value)
    return escape(text).replace("\n", "<br>")

  detail_lines: List[str] = []
  for label, value in summary_fields.items():
    detail_lines.append(
      f"<div class='detail-line'><span class='detail-label'>{cell(label)}</span><span class='detail-value'>{cell(value)}</span></div>"
    )

  def status_class(value: Any) -> str:
    normalized = str(value or "").strip().lower()
    if normalized == "pass":
      return "status-pass"
    if normalized == "fail":
      return "status-fail"
    if normalized == "skip":
      return "status-skip"
    return ""

  # Two-level grouping:
  # 1) Build-level shared fields: build/date/commit/user
  # 2) Chip-level shared fields: chip/compilation result/compilation runtime
  build_groups: Dict[str, List[Dict[str, Any]]] = {}
  build_order: List[str] = []
  for row in rows:
    build_key = str(row.get("build_number", "N/A"))
    if build_key not in build_groups:
      build_groups[build_key] = []
      build_order.append(build_key)
    build_groups[build_key].append(row)

  table_rows: List[str] = []
  for build_key in build_order:
    build_rows = build_groups.get(build_key, [])
    if not build_rows:
      continue
    build_row_span = len(build_rows)

    chip_groups: Dict[str, List[Dict[str, Any]]] = {}
    chip_order: List[str] = []
    for row in build_rows:
      chip_key = str(row.get("chip_name", "N/A"))
      if chip_key not in chip_groups:
        chip_groups[chip_key] = []
        chip_order.append(chip_key)
      chip_groups[chip_key].append(row)

    build_row_index = 0
    for chip_key in chip_order:
      chip_rows = chip_groups.get(chip_key, [])
      chip_row_span = len(chip_rows) or 1
      for chip_row_index, row in enumerate(chip_rows):
        row_cells: List[str] = []

        if build_row_index == 0 and chip_row_index == 0:
          row_cells.append(f"<td rowspan='{build_row_span}' class='group-cell'>{cell(row.get('build_number'))}</td>")
          row_cells.append(f"<td rowspan='{build_row_span}'>{cell(row.get('date'))}</td>")
          row_cells.append(f"<td rowspan='{build_row_span}'>{cell(row.get('commit_id'))}</td>")
          row_cells.append(f"<td rowspan='{build_row_span}'>{cell(row.get('username'))}</td>")

        if chip_row_index == 0:
          compilation_result = row.get("compilation_result")
          row_cells.append(f"<td rowspan='{chip_row_span}' class='group-cell'>{cell(row.get('chip_name'))}</td>")
          row_cells.append(
            f"<td rowspan='{chip_row_span}' class='{status_class(compilation_result)}'>{cell(compilation_result)}</td>"
          )
          row_cells.append(f"<td rowspan='{chip_row_span}'>{cell(row.get('compilation_run_time'))}</td>")

        simulation_result = row.get("simulation_result")
        row_cells.append(f"<td>{cell(row.get('case_name'))}</td>")
        row_cells.append(f"<td class='{status_class(simulation_result)}'>{cell(simulation_result)}</td>")
        row_cells.append(f"<td class='{status_class(simulation_result)}'>{cell(row.get('simulation_run_time'))}</td>")
        row_cells.append(f"<td class='{status_class(simulation_result)}'>{cell(row.get('host_seconds'))}</td>")
        table_rows.append("<tr>" + "".join(row_cells) + "</tr>")

        build_row_index += 1

  if not table_rows:
    table_rows.append("<tr><td colspan='11'>No rows available.</td></tr>")

  style = "  <link rel=\"stylesheet\" href=\"smoke_report.css\">"

  subtitle = "Grouped by CHIP_NAME with CASE_NAME rows underneath, and SIMULATION_RUN_TIME split into simSeconds and hostSeconds."

  return f"""<!DOCTYPE html>
<html lang='en'>
<head>
  <meta charset='utf-8'>
  <meta name='viewport' content='width=device-width, initial-scale=1'>
  <title>{cell(page_title)}</title>
  {style}
</head>
<body>
  <div class='page'>
    <div class='hero'>
      <h1>{cell(page_title)}</h1>
      <p>{cell(subtitle)}</p>
    </div>

    <div class='section-title'>General Info</div>
    <section class='detail-panel'>
      {''.join(detail_lines)}
    </section>

    <div class='section-title'>Run Details</div>
    <div class='table-wrap'>
      <table>
        <thead>
          <tr>
            <th rowspan='2'>BUILD_NUMBER</th>
            <th rowspan='2'>DATE</th>
            <th rowspan='2'>COMMIT_ID</th>
            <th rowspan='2'>USERNAME</th>
            <th rowspan='2'>CHIP_NAME</th>
            <th colspan='2'>COMPILATION</th>
            <th colspan='4'>SIMULATION</th>
          </tr>
          <tr>
            <th>RESULT</th>
            <th>RUN_TIME</th>
            <th>TESTCASE_NAME</th>
            <th>RESULT</th>
            <th>RUN_TIME</th>
            <th>HOST_TIME</th>
          </tr>
        </thead>
        <tbody>
          {''.join(table_rows)}
        </tbody>
      </table>
    </div>

    <div class='small'>Build rows are grouped by chip so one CHIP_NAME cell spans multiple CASE_NAME rows.</div>
  </div>
</body>
</html>
"""


def _build_report_payload(page_title: str, summary_fields: Dict[str, Any], rows: List[Dict[str, Any]]) -> Dict[str, Any]:
  """Build a JSON-friendly representation of the rendered report.
  This packages the report title, metadata, and rows into a structure for export.
  """
  return {
    "page_title": page_title,
    "generated_at": datetime.now().isoformat(),
    "summary_fields": summary_fields,
    "rows": rows,
  }


def generate_weekly_results_json(output_dir: Path, logger: Any) -> None:
  """Generate the JSON smoke report for the latest run directory.
  It writes the structured run summary and per-case rows to RESULTS/weekly_results.json.
  """
  summary_path = output_dir / "RESULTS" / "general_results.json"
  if not summary_path.exists():
    logger.warning(f"No general results found for JSON report: {summary_path}")
    return

  summary = json.loads(summary_path.read_text(encoding="utf-8"))
  build_number = output_dir.name
  rows = _collect_report_rows(summary, build_number)
  git_details = summary.get("git_details", {}) if isinstance(summary, dict) else {}
  summary_fields = {
    "Build Number": build_number,
    "Date": summary.get("timestamp", "N/A"),
    "Commit ID": git_details.get("commit_id", "N/A"),
    "Commit Message": git_details.get("commit_message", "N/A"),
    "User Name": git_details.get("pushed_by", "N/A"),
    "Git Files Change": ", ".join(git_details.get("changed_files", [])) if isinstance(git_details.get("changed_files", []), list) and git_details.get("changed_files", []) else "N/A",
  }
  report_path = output_dir / "RESULTS" / "weekly_results.json"
  report_path.write_text(
    json.dumps(_build_report_payload("Smoke Results", summary_fields, rows), indent=2),
    encoding="utf-8",
  )
  logger.warning(f"Wrote smoke JSON report: {report_path}")


def generate_weekly_results_html(output_dir: Path, logger: Any) -> None:
    """Generate the HTML smoke report for the latest run directory.
    It reads the general summary and writes a readable report page to disk.
    """
    summary_path = output_dir / "RESULTS" / "general_results.json"
    if not summary_path.exists():
        logger.warning(f"No general results found for HTML report: {summary_path}")
        return

    summary = json.loads(summary_path.read_text(encoding="utf-8"))
    build_number = output_dir.name
    rows = _collect_report_rows(summary, build_number)
    git_details = summary.get("git_details", {}) if isinstance(summary, dict) else {}
    summary_fields = {
        "Build Number": build_number,
        "Date": summary.get("timestamp", "N/A"),
        "Commit ID": git_details.get("commit_id", "N/A"),
        "Commit Message": git_details.get("commit_message", "N/A"),
        "User Name": git_details.get("pushed_by", "N/A"),
        "Git Files Change": ", ".join(git_details.get("changed_files", [])) if isinstance(git_details.get("changed_files", []), list) and git_details.get("changed_files", []) else "N/A",
        "Result Folder": str(output_dir / "RESULTS"),
        "Output Dir": summary.get("output_dir", "N/A"),
        "Binary Path": summary.get("compilation", {}).get("binary_path", "N/A") if isinstance(summary.get("compilation", {}), dict) else "N/A",
        "Compile Log": summary.get("compilation", {}).get("log_file", "N/A") if isinstance(summary.get("compilation", {}), dict) else "N/A",
    }
    html_text = render_weekly_results_html("Smoke Results", summary_fields, rows)
    report_path = output_dir / "RESULTS" / "weekly_results.html"
    (output_dir / "RESULTS" / _REPORT_CSS_FILENAME).write_text(_REPORT_CSS, encoding="utf-8")
    report_path.write_text(html_text, encoding="utf-8")
    logger.warning(f"Wrote smoke HTML report: {report_path}")


def generate_jenkins_history_weekly_results_html(history_dir: Path, logger: Any, limit: int = 30) -> None:
    """Generate the HTML history report from recent smoke runs.
    It writes the latest build snapshots into jenkins_history_weekly_results.html.
    """
    history_path = history_dir / "history_results.json"
    if not history_path.exists():
        logger.warning(f"No history file found for HTML report: {history_path}")
        return

    history_data = json.loads(history_path.read_text(encoding="utf-8"))
    runs = history_data.get("runs", {}) if isinstance(history_data, dict) else {}
    flattened_rows: List[Dict[str, Any]] = []

    if isinstance(runs, dict):
        for build_number, run_payload in runs.items():
            if not isinstance(run_payload, dict):
                continue
            summary = run_payload.get("general_results", {}) if isinstance(run_payload.get("general_results", {}), dict) else {}
            rows = _collect_report_rows(summary, build_number)
            run_timestamp = summary.get("timestamp") or run_payload.get("updated_at") or ""
            for row in rows:
                row["run_timestamp"] = run_timestamp
                flattened_rows.append(row)

    flattened_rows.sort(
        key=lambda item: (
            -_parse_iso_timestamp(item.get("run_timestamp") or item.get("date")),
            str(item.get("build_number", "")),
            str(item.get("chip_name", "")),
            str(item.get("case_name", "")),
        )
    )
    selected_rows = flattened_rows[:limit]

    latest_run_summary: Optional[Dict[str, Any]] = None
    latest_run_payload: Optional[Dict[str, Any]] = None
    if isinstance(runs, dict):
        for build_number, run_payload in runs.items():
            if isinstance(run_payload, dict):
                summary = run_payload.get("general_results", {}) if isinstance(run_payload.get("general_results", {}), dict) else {}
                if isinstance(summary, dict) and summary:
                    latest_run_summary = summary
                    latest_run_payload = run_payload
                    break

    git_details = latest_run_summary.get("git_details", {}) if isinstance(latest_run_summary, dict) else {}
    latest_output_dir = latest_run_payload.get("output_dir", "N/A") if isinstance(latest_run_payload, dict) else "N/A"
    summary_fields = {
        "History File": str(history_path),
        "Latest Build Number": history_data.get("latest_build_number", "N/A") if isinstance(history_data, dict) else "N/A",
        "Date": latest_run_summary.get("timestamp", "N/A") if isinstance(latest_run_summary, dict) else "N/A",
        "Commit ID": git_details.get("commit_id", "N/A"),
        "Commit Message": git_details.get("commit_message", "N/A"),
        "User Name": git_details.get("pushed_by", "N/A"),
        "Git Files Change": ", ".join(git_details.get("changed_files", [])) if isinstance(git_details.get("changed_files", []), list) and git_details.get("changed_files", []) else "N/A",
        "Result Folder": str(Path(str(latest_output_dir)) / "RESULTS") if latest_output_dir != "N/A" else "N/A",
        "Output Dir": latest_output_dir,
        "Binary Path": latest_run_summary.get("compilation", {}).get("binary_path", "N/A") if isinstance(latest_run_summary, dict) and isinstance(latest_run_summary.get("compilation", {}), dict) else "N/A",
        "Compile Log": latest_run_summary.get("compilation", {}).get("log_file", "N/A") if isinstance(latest_run_summary, dict) and isinstance(latest_run_summary.get("compilation", {}), dict) else "N/A",
        "Total Runs": history_data.get("total_runs", 0) if isinstance(history_data, dict) else 0,
        "Rows Included": len(selected_rows),
    }

    html_text = render_weekly_results_html("Jenkins History Smoke Results", summary_fields, selected_rows)
    report_path = history_dir / "jenkins_history_weekly_results.html"
    (history_dir / _REPORT_CSS_FILENAME).write_text(_REPORT_CSS, encoding="utf-8")
    report_path.write_text(html_text, encoding="utf-8")
    logger.warning(f"Wrote Jenkins history HTML report: {report_path}")


def generate_jenkins_history_weekly_results_json(history_dir: Path, logger: Any, limit: int = 30) -> None:
    """Generate the JSON history report from recent smoke runs.
    It exports the latest history rows in a machine-readable format.
    """
    history_path = history_dir / "history_results.json"
    if not history_path.exists():
        logger.warning(f"No history file found for JSON report: {history_path}")
        return

    history_data = json.loads(history_path.read_text(encoding="utf-8"))
    runs = history_data.get("runs", {}) if isinstance(history_data, dict) else {}
    flattened_rows: List[Dict[str, Any]] = []

    if isinstance(runs, dict):
        for build_number, run_payload in runs.items():
            if not isinstance(run_payload, dict):
                continue
            summary = run_payload.get("general_results", {}) if isinstance(run_payload.get("general_results", {}), dict) else {}
            rows = _collect_report_rows(summary, build_number)
            run_timestamp = summary.get("timestamp") or run_payload.get("updated_at") or ""
            for row in rows:
                row["run_timestamp"] = run_timestamp
                flattened_rows.append(row)

    flattened_rows.sort(
        key=lambda item: (
            -_parse_iso_timestamp(item.get("run_timestamp") or item.get("date")),
            str(item.get("build_number", "")),
            str(item.get("chip_name", "")),
            str(item.get("case_name", "")),
        )
    )
    selected_rows = flattened_rows[:limit]

    latest_run_summary: Optional[Dict[str, Any]] = None
    latest_run_payload: Optional[Dict[str, Any]] = None
    if isinstance(runs, dict):
        for build_number, run_payload in runs.items():
            if isinstance(run_payload, dict):
                summary = run_payload.get("general_results", {}) if isinstance(run_payload.get("general_results", {}), dict) else {}
                if isinstance(summary, dict) and summary:
                    latest_run_summary = summary
                    latest_run_payload = run_payload
                    break

    git_details = latest_run_summary.get("git_details", {}) if isinstance(latest_run_summary, dict) else {}
    latest_output_dir = latest_run_payload.get("output_dir", "N/A") if isinstance(latest_run_payload, dict) else "N/A"
    summary_fields = {
        "History File": str(history_path),
        "Latest Build Number": history_data.get("latest_build_number", "N/A") if isinstance(history_data, dict) else "N/A",
        "Date": latest_run_summary.get("timestamp", "N/A") if isinstance(latest_run_summary, dict) else "N/A",
        "Commit ID": git_details.get("commit_id", "N/A"),
        "Commit Message": git_details.get("commit_message", "N/A"),
        "User Name": git_details.get("pushed_by", "N/A"),
        "Git Files Change": ", ".join(git_details.get("changed_files", [])) if isinstance(git_details.get("changed_files", []), list) and git_details.get("changed_files", []) else "N/A",
        "Result Folder": str(Path(str(latest_output_dir)) / "RESULTS") if latest_output_dir != "N/A" else "N/A",
        "Output Dir": latest_output_dir,
        "Binary Path": latest_run_summary.get("compilation", {}).get("binary_path", "N/A") if isinstance(latest_run_summary, dict) and isinstance(latest_run_summary.get("compilation", {}), dict) else "N/A",
        "Compile Log": latest_run_summary.get("compilation", {}).get("log_file", "N/A") if isinstance(latest_run_summary, dict) and isinstance(latest_run_summary.get("compilation", {}), dict) else "N/A",
        "Total Runs": history_data.get("total_runs", 0) if isinstance(history_data, dict) else 0,
        "Rows Included": len(selected_rows),
    }

    report_path = history_dir / "jenkins_history_weekly_results.json"
    report_path.write_text(
        json.dumps(_build_report_payload("Jenkins History Smoke Results", summary_fields, selected_rows), indent=2),
        encoding="utf-8",
    )
    logger.warning(f"Wrote Jenkins history JSON report: {report_path}")