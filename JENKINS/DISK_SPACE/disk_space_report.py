#!/usr/bin/env python3
"""Walk a directory tree and report per-directory disk usage as JSON, text, and HTML."""

from __future__ import annotations

import argparse
import json
import os
from datetime import datetime, timezone
from html import escape
from pathlib import Path
from typing import Any, Dict, List, Optional

_REPORT_CSS_FILENAME = "disk_space_report.css"
_REPORT_CSS = """:root {
  color-scheme: light;
  --bg: #f6f8fb;
  --panel: #ffffff;
  --border: #dbe3ee;
  --heading: #14213d;
  --muted: #667085;
  --accent: #1f3a5f;
}
body { margin: 0; background: var(--bg); color: var(--heading); font-family: Arial, Helvetica, sans-serif; }
.page { max-width: 1400px; margin: 0 auto; padding: 24px; }
.hero {
  background: var(--panel);
  border: 1px solid var(--border);
  border-radius: 16px;
  padding: 20px 22px;
  box-shadow: 0 6px 24px rgba(15, 23, 42, 0.06);
  margin-bottom: 18px;
}
.hero h1 { margin: 0 0 6px 0; font-size: 26px; }
.hero p { margin: 0; color: var(--muted); line-height: 1.5; }
table { width: 100%; border-collapse: collapse; background: var(--panel); border: 1px solid var(--border); border-radius: 12px; overflow: hidden; }
th, td { text-align: left; padding: 8px 12px; border-bottom: 1px solid #eef2f7; font-size: 13px; }
th { background: #eef3f8; color: var(--accent); }
td.size { text-align: right; white-space: nowrap; font-variant-numeric: tabular-nums; }
td.bar-cell { min-width: 160px; }
.bar-track { background: #eef2f7; border-radius: 6px; height: 10px; overflow: hidden; }
.bar-fill { background: var(--accent); height: 100%; }
tr.depth-0 td.name { font-weight: 700; }
tr.depth-1 td.name { padding-left: 28px; }
tr.depth-2 td.name { padding-left: 44px; }
tr.depth-3 td.name { padding-left: 60px; }
tr.depth-4 td.name { padding-left: 76px; }
tr.depth-5 td.name { padding-left: 92px; }
tr.over-limit td { background: #fdecea; color: #b42318; font-weight: 700; }
tr.over-limit .bar-fill { background: #b42318; }
"""

# Directories at or above this size are flagged red in the HTML report.
OVER_LIMIT_BYTES = 500 * 1024 ** 3


def log(message: str) -> None:
    """Print a timestamped, unbuffered progress message."""
    timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")
    print(f"[{timestamp}] [DISK_SPACE] {message}", flush=True)


def human_size(num_bytes: int) -> str:
    """Format a byte count as a human-readable string, for example 12.3 GB."""
    value = float(num_bytes)
    for unit in ("B", "KB", "MB", "GB", "TB", "PB"):
        if value < 1024.0 or unit == "PB":
            return f"{value:.2f} {unit}" if unit != "B" else f"{int(value)} B"
        value /= 1024.0
    return f"{value:.2f} PB"


def compute_directory_sizes(root: Path, exclude_dirs: Optional[set[str]] = None) -> Dict[str, Dict[str, int]]:
    """Return {absolute_path: {size_bytes, file_count, dir_count}} for root and every subdirectory.

    Paths in exclude_dirs (for example the reserved DISK_SPACE reports folder) are pruned entirely
    so a report never inflates the size of the directory it was generated for.
    """
    exclude_dirs = exclude_dirs or set()
    stats: Dict[str, Dict[str, int]] = {}
    for current_dir, subdirs, files in os.walk(root, topdown=False, followlinks=False):
        subdirs[:] = [name for name in subdirs if os.path.join(current_dir, name) not in exclude_dirs]
        if current_dir in exclude_dirs:
            continue
        total_size = 0
        file_count = 0
        for file_name in files:
            file_path = os.path.join(current_dir, file_name)
            try:
                if os.path.islink(file_path):
                    continue
                total_size += os.path.getsize(file_path)
                file_count += 1
            except OSError:
                continue
        dir_count = 0
        for subdir_name in subdirs:
            subdir_path = os.path.join(current_dir, subdir_name)
            if os.path.islink(subdir_path):
                continue
            child_stats = stats.get(subdir_path)
            if child_stats is None:
                continue
            total_size += child_stats["size_bytes"]
            file_count += child_stats["file_count"]
            dir_count += 1 + child_stats["dir_count"]
        stats[current_dir] = {"size_bytes": total_size, "file_count": file_count, "dir_count": dir_count}
    return stats


def build_tree(root: Path, stats: Dict[str, Dict[str, int]], top_n: Optional[int], max_depth: Optional[int], exclude_dirs: Optional[set[str]] = None) -> Dict[str, Any]:
    """Build a nested tree, sorted by size descending, honoring optional --top and --max-depth limits."""
    exclude_dirs = exclude_dirs or set()

    def node_for(path: Path, depth: int) -> Dict[str, Any]:
        path_str = str(path)
        entry_stats = stats.get(path_str, {"size_bytes": 0, "file_count": 0, "dir_count": 0})
        node: Dict[str, Any] = {
            "name": path.name or str(path),
            "path": path_str,
            "depth": depth,
            "size_bytes": entry_stats["size_bytes"],
            "size_human": human_size(entry_stats["size_bytes"]),
            "file_count": entry_stats["file_count"],
            "dir_count": entry_stats["dir_count"],
            "over_limit": entry_stats["size_bytes"] >= OVER_LIMIT_BYTES,
            "children": [],
        }
        if max_depth is not None and depth >= max_depth:
            return node
        try:
            subdirs = [child for child in path.iterdir() if child.is_dir() and not child.is_symlink() and str(child) not in exclude_dirs]
        except OSError:
            subdirs = []
        subdirs.sort(key=lambda child: stats.get(str(child), {"size_bytes": 0})["size_bytes"], reverse=True)
        if top_n:
            subdirs = subdirs[:top_n]
        node["children"] = [node_for(child, depth + 1) for child in subdirs]
        return node

    return node_for(root, 0)


def flatten_tree(node: Dict[str, Any], rows: Optional[List[Dict[str, Any]]] = None) -> List[Dict[str, Any]]:
    """Flatten the nested tree into an ordered list of rows for table-style rendering."""
    if rows is None:
        rows = []
    rows.append(node)
    for child in node["children"]:
        flatten_tree(child, rows)
    return rows


def render_text_tree(node: Dict[str, Any], lines: Optional[List[str]] = None) -> List[str]:
    """Render an indented, du-style plain-text tree with sizes."""
    if lines is None:
        lines = []
    indent = "  " * node["depth"]
    lines.append(f"{indent}{node['size_human']:>10}  {node['name']}")
    for child in node["children"]:
        render_text_tree(child, lines)
    return lines


def render_html(input_dir: Path, generated_at: str, root_node: Dict[str, Any]) -> str:
    """Render the disk space report as a standalone HTML page with an external CSS file."""
    rows = flatten_tree(root_node)
    largest = max((row["size_bytes"] for row in rows), default=1) or 1
    body_rows = []
    for row in rows:
        percent = round((row["size_bytes"] / largest) * 100.0, 1)
        classes = [f"depth-{min(row['depth'], 5)}"]
        if row["size_bytes"] >= OVER_LIMIT_BYTES:
            classes.append("over-limit")
        body_rows.append(
            f"<tr class=\"{' '.join(classes)}\">"
            f"<td class=\"name\">{escape(row['name'])}</td>"
            f"<td class=\"size\">{escape(row['size_human'])}</td>"
            f"<td class=\"size\">{row['file_count']}</td>"
            f"<td class=\"size\">{row['dir_count']}</td>"
            f"<td class=\"bar-cell\"><div class=\"bar-track\"><div class=\"bar-fill\" style=\"width:{percent}%\"></div></div></td>"
            f"<td>{escape(row['path'])}</td>"
            "</tr>"
        )
    return (
        "<!DOCTYPE html><html lang=\"en\"><head><meta charset=\"utf-8\">"
        f"<title>Disk Space Report - {escape(str(input_dir))}</title>"
        f"<link rel=\"stylesheet\" href=\"{_REPORT_CSS_FILENAME}\"></head><body>"
        "<div class=\"page\">"
        "<div class=\"hero\"><h1>Disk Space Report</h1>"
        f"<p>Input directory: {escape(str(input_dir))}<br>"
        f"Total size: {escape(root_node['size_human'])} across {root_node['dir_count']} directories and {root_node['file_count']} files.<br>"
        f"Directories at or above 500 GB are highlighted red.<br>"
        f"Generated at: {escape(generated_at)}</p></div>"
        "<table><thead><tr><th>Directory</th><th>Size</th><th>Files</th><th>Subdirectories</th><th>Relative size</th><th>Full path</th></tr></thead>"
        f"<tbody>{''.join(body_rows)}</tbody></table>"
        "</div></body></html>"
    )


def parse_args() -> argparse.Namespace:
    """Parse CLI options for the disk space report generator."""
    parser = argparse.ArgumentParser(
        description="Walk a directory and report per-directory disk usage as JSON, text, and HTML.",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument("--input-dir", required=True, help="Required root directory to scan.")
    parser.add_argument("--output-dir", default="", help="Directory to write the reports into. Defaults to <input-dir>/DISK_SPACE/DISK_SPACE_BUILD_<BUILD_NUMBER> (or a timestamped folder outside Jenkins).")
    parser.add_argument("--max-depth", type=int, default=None, help="Maximum directory depth to descend into. Unlimited by default.")
    parser.add_argument("--top", type=int, default=0, help="Only show the N largest subdirectories per level. 0 shows all.")
    parser.add_argument("--dry-run", action="store_true", help="Scan and print a preview summary without writing any JSON/HTML/text report files.")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    input_dir = Path(args.input_dir).expanduser().resolve()
    if not input_dir.is_dir():
        raise SystemExit(f"DISK_SPACE BLOCKED: input directory does not exist: {input_dir}")

    # The reserved DISK_SPACE reports folder at the top of input_dir is always excluded from the
    # scan, so a report never inflates the size of the directory it was generated for, and repeat
    # runs do not accumulate size from earlier report folders.
    reserved_reports_dir = str(input_dir / "DISK_SPACE")
    exclude_dirs = {reserved_reports_dir}

    if args.dry_run:
        log(f"[DRY RUN] Scanning {input_dir} (max_depth={args.max_depth}, top={args.top or 'ALL'})...")
        stats = compute_directory_sizes(input_dir, exclude_dirs)
        root_node = build_tree(input_dir, stats, args.top or None, args.max_depth, exclude_dirs)
        over_limit_rows = [row for row in flatten_tree(root_node) if row["over_limit"]]
        log(f"[DRY RUN] Total size: {root_node['size_human']} across {root_node['dir_count']} directories and {root_node['file_count']} files.")
        if over_limit_rows:
            log(f"[DRY RUN] WARNING: {len(over_limit_rows)} director(y/ies) are at or above the 500 GB mark.")
        for line in render_text_tree(root_node)[:20]:
            print(f"[DRY RUN] {line}")
        print("[DRY RUN] No JSON, HTML, or text report files were written.")
        print(json.dumps({
            "mode": "dry_run",
            "input_dir": str(input_dir),
            "total_size_human": root_node["size_human"],
            "total_dirs": root_node["dir_count"],
            "total_files": root_node["file_count"],
            "over_limit_directories": len(over_limit_rows),
        }, indent=2))
        return 0

    if args.output_dir.strip():
        output_dir = Path(args.output_dir).expanduser().resolve()
    else:
        build_number = os.environ.get("BUILD_NUMBER", "").strip()
        if build_number:
            folder_name = f"DISK_SPACE_BUILD_{build_number}"
        else:
            timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
            folder_name = f"DISK_SPACE_REPORT_{timestamp}"
        # Default: nest results inside the scanned directory itself, e.g. <input_dir>/DISK_SPACE/DISK_SPACE_BUILD_<N>.
        output_dir = input_dir / "DISK_SPACE" / folder_name

    log(f"Scanning {input_dir} (max_depth={args.max_depth}, top={args.top or 'ALL'})...")
    stats = compute_directory_sizes(input_dir, exclude_dirs)
    root_node = build_tree(input_dir, stats, args.top or None, args.max_depth, exclude_dirs)
    generated_at = datetime.now(timezone.utc).isoformat()
    log(f"Scan complete: {root_node['size_human']} across {root_node['dir_count']} directories and {root_node['file_count']} files.")
    over_limit_rows = [row for row in flatten_tree(root_node) if row["over_limit"]]
    if over_limit_rows:
        log(f"WARNING: {len(over_limit_rows)} director(y/ies) are at or above the 500 GB mark.")

    output_dir.mkdir(parents=True, exist_ok=True)
    summary = {
        "input_dir": str(input_dir),
        "generated_at": generated_at,
        "total_size_bytes": root_node["size_bytes"],
        "total_size_human": root_node["size_human"],
        "total_files": root_node["file_count"],
        "total_dirs": root_node["dir_count"],
        "max_depth": args.max_depth,
        "top": args.top or None,
        "over_limit_bytes": OVER_LIMIT_BYTES,
        "over_limit_directories": len(over_limit_rows),
        "tree": root_node,
    }
    json_path = output_dir / "disk_space_report.json"
    json_path.write_text(json.dumps(summary, indent=2), encoding="utf-8")
    log(f"Wrote JSON report: {json_path}")

    text_lines = render_text_tree(root_node)
    text_path = output_dir / "disk_space_tree.txt"
    text_path.write_text("\n".join(text_lines) + "\n", encoding="utf-8")
    log(f"Wrote text tree: {text_path}")

    (output_dir / _REPORT_CSS_FILENAME).write_text(_REPORT_CSS, encoding="utf-8")
    html_path = output_dir / "disk_space_report.html"
    html_path.write_text(render_html(input_dir, generated_at, root_node), encoding="utf-8")
    log(f"Wrote HTML report: {html_path}")

    print(json.dumps({"total_size_human": summary["total_size_human"], "total_dirs": summary["total_dirs"], "total_files": summary["total_files"], "output_dir": str(output_dir)}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
