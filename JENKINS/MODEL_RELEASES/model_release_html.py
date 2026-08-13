#!/usr/bin/env python3
"""HTML report generation for one model-unit release version."""

from __future__ import annotations

import html
from pathlib import Path
from typing import Any, Dict, List


def write_release_report(release_dir: Path, manifest: Dict[str, Any]) -> Path:
    """Write a standalone HTML report for one model-unit/version release."""
    rows: List[str] = []
    for chip_name, testcases in manifest.get("simulation", {}).items():
        for testcase, result in testcases.items():
            rows.append(
                "<tr><td>{}</td><td>{}</td><td class='status-{}'>{}</td><td>{}</td><td>{}</td><td>{}</td></tr>".format(
                    html.escape(str(chip_name)),
                    html.escape(str(testcase)),
                    html.escape(str(result.get("status", "N/A")).lower()),
                    html.escape(str(result.get("status", "N/A"))),
                    html.escape(str(result.get("return_code", "N/A"))),
                    html.escape(str(result.get("runtime_seconds", "N/A"))),
                    html.escape(str(result.get("stats_file", "N/A"))),
                )
            )

    report_path = release_dir / "release_report.html"
    report_path.write_text(
        "<!doctype html><html><head><meta charset='utf-8'><title>Model Release</title>"
        "<style>body{font-family:Arial,sans-serif;margin:24px;color:#14213d}"
        "table{border-collapse:collapse;width:100%}th,td{border:1px solid #dbe3ee;padding:8px;text-align:left;font-size:12px}"
        "th{background:#1f3a5f;color:#fff}.status-pass{background:#d9f2c2}.status-fail{background:#ffd6d6}.status-skip{background:#fff0c2}</style>"
        f"</head><body><h1>{html.escape(str(manifest['release_name']))}</h1>"
        f"<p><b>Model unit:</b> {html.escape(str(manifest['model_unit_name']))}<br>"
        f"<b>Version:</b> {html.escape(str(manifest['version']))}<br>"
        f"<b>Branch:</b> {html.escape(str(manifest['branch']))}<br>"
        f"<b>Commit:</b> {html.escape(str(manifest['commit_id']))}</p>"
        f"<h2>Summary</h2><p>{html.escape(str(manifest['summary']))}</p>"
        f"<h2>Fixes</h2><p>{html.escape(str(manifest['fixes']))}</p>"
        "<h2>Compilation and Simulation</h2><table><thead><tr><th>CHIP_NAME</th><th>TESTCASE</th><th>STATUS</th><th>RETURN_CODE</th><th>RUNTIME_SECONDS</th><th>STATS_FILE</th></tr></thead>"
        f"<tbody>{''.join(rows) or '<tr><td colspan=6>No testcase results.</td></tr>'}</tbody></table></body></html>",
        encoding="utf-8",
    )
    return report_path
