#!/usr/bin/env python3
"""
DevFlow - TODO/FIXME 标记扫描器
扫描项目中的 TODO/FIXME/XXX/HACK 标记，按优先级分类并统计
Usage: python todo-scan.py --dir .
       python todo-scan.py --file foo.py
       python todo-scan.py --dir . --format json
"""

import argparse
import json
import os
import re
import sys
from pathlib import Path
from datetime import datetime

# 需要扫描的文件扩展名
EXTENSIONS = {".py", ".js", ".ts", ".tsx", ".jsx", ".java", ".go", ".c", ".cpp",
              ".rs", ".rb", ".php", ".html", ".css", ".sh", ".md"}
# 忽略的目录
IGNORE_DIRS = {"node_modules", ".git", "__pycache__", "dist", "build", ".next",
               "target", "vendor", ".venv", "venv"}

# 标记类型定义：类型 -> (正则模式, 严重级别)
MARKERS = [
    ("HACK", re.compile(r"\bHACK\b"), "高"),
    ("FIXME", re.compile(r"\bFIXME\b"), "高"),
    ("BUG", re.compile(r"\bBUG\b"), "高"),
    ("TODO", re.compile(r"\bTODO\b"), "中"),
    ("XXX", re.compile(r"\bXXX\b"), "中"),
    ("OPTIMIZE", re.compile(r"\bOPTIMIZE\b"), "低"),
    ("NOTE", re.compile(r"\bNOTE\b"), "低"),
]


def scan_file(filepath):
    """扫描单个文件，返回标记列表"""
    results = []
    try:
        content = Path(filepath).read_text(encoding="utf-8", errors="ignore")
    except Exception:
        return results

    for i, line in enumerate(content.split("\n"), 1):
        for marker_name, pattern, severity in MARKERS:
            if pattern.search(line):
                # 提取标记后面的内容作为描述
                match = pattern.search(line)
                desc = line[match.end():].strip()
                if desc.startswith(":") or desc.startswith("-"):
                    desc = desc[1:].strip()
                if desc.startswith(("(", "[")):
                    desc = desc.strip("()[] ")

                results.append({
                    "file": filepath,
                    "line": i,
                    "marker": marker_name,
                    "severity": severity,
                    "description": desc or "(无描述)"
                })
                break  # 一行只记一个标记
    return results


def scan_dir(dirpath):
    """扫描整个目录"""
    all_results = []
    for root, dirs, files in os.walk(dirpath):
        dirs[:] = [d for d in dirs if d not in IGNORE_DIRS]
        for f in files:
            if Path(f).suffix in EXTENSIONS:
                fp = os.path.join(root, f)
                all_results.extend(scan_file(fp))
    return all_results


def print_report(results, output_format="text"):
    """输出报告"""
    if output_format == "json":
        print(json.dumps({"total": len(results), "items": results},
                         ensure_ascii=False, indent=2))
        return

    if not results:
        print("✓ 未发现 TODO/FIXME 等标记")
        return

    # 按严重级别分组统计
    by_severity = {"高": 0, "中": 0, "低": 0}
    by_marker = {}
    for r in results:
        by_severity[r["severity"]] += 1
        by_marker[r["marker"]] = by_marker.get(r["marker"], 0) + 1

    print(f"共发现 {len(results)} 处标记：")
    print(f"  高优先级: {by_severity['高']} | 中优先级: {by_severity['中']} | 低优先级: {by_severity['低']}")
    print(f"  类型分布: " + ", ".join(f"{k}×{v}" for k, v in sorted(by_marker.items())))
    print("")

    # 高优先级优先展示
    severity_order = {"高": 0, "中": 1, "低": 2}
    for r in sorted(results, key=lambda x: (severity_order[x["severity"]], x["file"])):
        print(f"  [{r['severity']}] {r['marker']}: {r['file']}:{r['line']}")
        print(f"        {r['description']}")


def main():
    parser = argparse.ArgumentParser(description="DevFlow TODO/FIXME 标记扫描器")
    parser.add_argument("--dir", default=".", help="要扫描的目录")
    parser.add_argument("--file", help="要扫描的单个文件")
    parser.add_argument("--format", choices=["text", "json"], default="text",
                        help="输出格式")
    args = parser.parse_args()

    if args.file:
        results = scan_file(args.file)
    else:
        results = scan_dir(args.dir)

    print_report(results, args.format)

    # JSON 模式静默退出
    if args.format == "json":
        return

    # 存在高优先级标记时返回非零退出码
    if any(r["severity"] == "高" for r in results):
        sys.exit(1)


if __name__ == "__main__":
    main()
