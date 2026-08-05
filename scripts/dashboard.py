#!/usr/bin/env python3
"""
DevFlow - Code Quality Dashboard
生成代码质量报告和趋势图
Usage:
  python dashboard.py --dir .
  python dashboard.py --dir . --format json
  python dashboard.py --dir . --output report.html
  python dashboard.py --trend --days 30
"""

import argparse
import json
import os
import re
import sys
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Tuple
from collections import defaultdict

# 代码度量指标
class CodeMetrics:
    def __init__(self):
        self.total_files = 0
        self.total_lines = 0
        self.code_lines = 0
        self.comment_lines = 0
        self.blank_lines = 0
        self.functions = 0
        self.classes = 0
        self.avg_function_length = 0
        self.max_function_length = 0
        self.avg_complexity = 0
        self.max_complexity = 0
        self.duplicate_lines = 0
        self.test_coverage = 0.0
        self.issues = {
            "critical": 0,
            "warning": 0,
            "info": 0
        }


def count_lines(content: str) -> Tuple[int, int, int]:
    """统计代码行、注释行、空行"""
    code = 0
    comment = 0
    blank = 0

    in_block_comment = False

    for line in content.split("\n"):
        stripped = line.strip()

        if not stripped:
            blank += 1
            continue

        # 块注释
        if in_block_comment:
            comment += 1
            if "*/" in stripped:
                in_block_comment = False
            continue

        if stripped.startswith("/*"):
            comment += 1
            if "*/" not in stripped:
                in_block_comment = True
            continue

        # 行注释
        if stripped.startswith(("//", "#", "<!--")):
            comment += 1
            continue

        code += 1

    return code, comment, blank


def count_functions(content: str, ext: str) -> List[Dict]:
    """统计函数"""
    functions = []

    if ext == ".py":
        pattern = r"def\s+(\w+)\s*\(([^)]*)\)"
    elif ext in (".js", ".ts", ".jsx", ".tsx"):
        pattern = r"(?:function\s+(\w+)|(?:const|let|var)\s+(\w+)\s*=\s*(?:function|\([^)]*\)\s*=>))"
    elif ext == ".java":
        pattern = r"(?:public|private|protected|static)\s+\w+\s+(\w+)\s*\("
    elif ext == ".go":
        pattern = r"func\s+(?:\([^)]+\)\s+)?(\w+)\s*\("
    else:
        return functions

    for match in re.finditer(pattern, content):
        name = match.group(1) or match.group(2) if match.lastindex >= 2 else match.group(1)
        if name:
            functions.append({"name": name, "line": content[:match.start()].count("\n") + 1})

    return functions


def calculate_complexity(content: str) -> int:
    """计算圈复杂度（简化版）"""
    complexity = 1  # 基础复杂度

    # 控制流语句
    patterns = [
        r"\bif\b", r"\belse\b", r"\belif\b", r"\bfor\b", r"\bwhile\b",
        r"\bcase\b", r"\bcatch\b", r"\b\?\b", r"&&", r"\|\|",
        r"\btry\b", r"\bexcept\b", r"\bfinally\b"
    ]

    for pattern in patterns:
        complexity += len(re.findall(pattern, content))

    return complexity


def analyze_file(file_path: str) -> Dict:
    """分析单个文件"""
    try:
        content = Path(file_path).read_text(encoding="utf-8", errors="ignore")
        ext = Path(file_path).suffix

        code, comment, blank = count_lines(content)
        functions = count_functions(content, ext)
        complexity = calculate_complexity(content)

        # 计算函数长度
        func_lengths = []
        lines = content.split("\n")
        for i, func in enumerate(functions):
            start = func["line"] - 1
            # 简单估算函数长度
            end = len(lines)
            if i + 1 < len(functions):
                end = functions[i + 1]["line"] - 1
            func_lengths.append(end - start)

        return {
            "file": file_path,
            "ext": ext,
            "total_lines": len(lines),
            "code_lines": code,
            "comment_lines": comment,
            "blank_lines": blank,
            "functions": len(functions),
            "complexity": complexity,
            "avg_function_length": sum(func_lengths) / len(func_lengths) if func_lengths else 0,
            "max_function_length": max(func_lengths) if func_lengths else 0,
            "comment_ratio": comment / (code + comment) if (code + comment) > 0 else 0
        }
    except Exception as e:
        return {"file": file_path, "error": str(e)}


def scan_directory(directory: str) -> List[Dict]:
    """扫描目录"""
    results = []
    dir_path = Path(directory)

    # 支持的文件扩展名
    extensions = {".py", ".js", ".ts", ".jsx", ".tsx", ".java", ".go", ".rs", ".c", ".cpp", ".rb", ".php"}

    for file_path in dir_path.rglob("*"):
        # 跳过忽略的目录
        if any(part.startswith(".") or part in ("node_modules", "vendor", "dist", "build", "__pycache__")
               for part in file_path.parts):
            continue

        if file_path.suffix in extensions and file_path.is_file():
            result = analyze_file(str(file_path))
            if "error" not in result:
                results.append(result)

    return results


def calculate_summary(results: List[Dict]) -> CodeMetrics:
    """计算汇总指标"""
    metrics = CodeMetrics()

    if not results:
        return metrics

    metrics.total_files = len(results)
    metrics.total_lines = sum(r["total_lines"] for r in results)
    metrics.code_lines = sum(r["code_lines"] for r in results)
    metrics.comment_lines = sum(r["comment_lines"] for r in results)
    metrics.blank_lines = sum(r["blank_lines"] for r in results)
    metrics.functions = sum(r["functions"] for r in results)
    metrics.avg_function_length = sum(r["avg_function_length"] for r in results) / len(results)
    metrics.max_function_length = max(r["max_function_length"] for r in results)
    metrics.avg_complexity = sum(r["complexity"] for r in results) / len(results)
    metrics.max_complexity = max(r["complexity"] for r in results)

    # 计算整体注释率
    if metrics.code_lines + metrics.comment_lines > 0:
        metrics.test_coverage = metrics.comment_lines / (metrics.code_lines + metrics.comment_lines)

    return metrics


def generate_html_report(summary: CodeMetrics, details: List[Dict]) -> str:
    """生成 HTML 报告"""
    html = f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>DevFlow Code Quality Dashboard</title>
    <style>
        body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; margin: 0; padding: 20px; background: #f5f5f5; }}
        .container {{ max-width: 1200px; margin: 0 auto; }}
        .header {{ background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; padding: 30px; border-radius: 10px; margin-bottom: 20px; }}
        .cards {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 15px; margin-bottom: 20px; }}
        .card {{ background: white; padding: 20px; border-radius: 10px; box-shadow: 0 2px 10px rgba(0,0,0,0.1); }}
        .card h3 {{ margin: 0 0 10px 0; color: #666; font-size: 14px; }}
        .card .value {{ font-size: 32px; font-weight: bold; color: #333; }}
        .chart {{ background: white; padding: 20px; border-radius: 10px; box-shadow: 0 2px 10px rgba(0,0,0,0.1); margin-bottom: 20px; }}
        .bar {{ height: 20px; background: #667eea; border-radius: 10px; margin: 5px 0; }}
        .table {{ width: 100%; border-collapse: collapse; }}
        .table th, .table td {{ padding: 12px; text-align: left; border-bottom: 1px solid #eee; }}
        .table th {{ background: #f8f9fa; font-weight: 600; }}
        .good {{ color: #28a745; }}
        .warning {{ color: #ffc107; }}
        .danger {{ color: #dc3545; }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>DevFlow Code Quality Dashboard</h1>
            <p>Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</p>
        </div>

        <div class="cards">
            <div class="card">
                <h3>Total Files</h3>
                <div class="value">{summary.total_files}</div>
            </div>
            <div class="card">
                <h3>Total Lines</h3>
                <div class="value">{summary.total_lines:,}</div>
            </div>
            <div class="card">
                <h3>Code Lines</h3>
                <div class="value">{summary.code_lines:,}</div>
            </div>
            <div class="card">
                <h3>Functions</h3>
                <div class="value">{summary.functions}</div>
            </div>
            <div class="card">
                <h3>Avg Complexity</h3>
                <div class="value {'good' if summary.avg_complexity < 10 else 'warning' if summary.avg_complexity < 20 else 'danger'}">{summary.avg_complexity:.1f}</div>
            </div>
            <div class="card">
                <h3>Comment Ratio</h3>
                <div class="value">{summary.test_coverage:.1%}</div>
            </div>
        </div>

        <div class="chart">
            <h2>File Distribution</h2>
"""

    # 按扩展名统计
    ext_counts = defaultdict(int)
    for r in details:
        ext_counts[r["ext"]] += 1

    for ext, count in sorted(ext_counts.items(), key=lambda x: -x[1]):
        percentage = count / len(details) * 100
        html += f"""
            <div style="display: flex; align-items: center; margin: 10px 0;">
                <span style="width: 80px; font-weight: bold;">{ext}</span>
                <div style="flex: 1; background: #eee; border-radius: 10px; overflow: hidden;">
                    <div class="bar" style="width: {percentage}%"></div>
                </div>
                <span style="width: 50px; text-align: right;">{count}</span>
            </div>
"""

    html += """
        </div>

        <div class="chart">
            <h2>Top Complex Files</h2>
            <table class="table">
                <thead>
                    <tr>
                        <th>File</th>
                        <th>Lines</th>
                        <th>Functions</th>
                        <th>Complexity</th>
                        <th>Comment Ratio</th>
                    </tr>
                </thead>
                <tbody>
"""

    # 按复杂度排序
    sorted_details = sorted(details, key=lambda x: x.get("complexity", 0), reverse=True)[:20]

    for r in sorted_details:
        complexity_class = "good" if r["complexity"] < 10 else "warning" if r["complexity"] < 20 else "danger"
        html += f"""
                    <tr>
                        <td>{Path(r['file']).name}</td>
                        <td>{r['total_lines']}</td>
                        <td>{r['functions']}</td>
                        <td class="{complexity_class}">{r['complexity']}</td>
                        <td>{r['comment_ratio']:.1%}</td>
                    </tr>
"""

    html += """
                </tbody>
            </table>
        </div>
    </div>
</body>
</html>
"""

    return html


def format_report(summary: CodeMetrics, details: List[Dict], format: str = "text") -> str:
    """格式化报告"""
    if format == "json":
        return json.dumps({
            "summary": {
                "total_files": summary.total_files,
                "total_lines": summary.total_lines,
                "code_lines": summary.code_lines,
                "comment_lines": summary.comment_lines,
                "blank_lines": summary.blank_lines,
                "functions": summary.functions,
                "avg_function_length": summary.avg_function_length,
                "max_function_length": summary.max_function_length,
                "avg_complexity": summary.avg_complexity,
                "max_complexity": summary.max_complexity,
                "comment_ratio": summary.test_coverage
            },
            "files": details[:50]  # 限制输出数量
        }, indent=2, ensure_ascii=False)

    lines = []
    lines.append("=" * 60)
    lines.append("DevFlow Code Quality Dashboard")
    lines.append("=" * 60)
    lines.append("")
    lines.append("[Summary]")
    lines.append(f"  Total Files:      {summary.total_files}")
    lines.append(f"  Total Lines:      {summary.total_lines:,}")
    lines.append(f"  Code Lines:       {summary.code_lines:,}")
    lines.append(f"  Comment Lines:    {summary.comment_lines:,}")
    lines.append(f"  Blank Lines:      {summary.blank_lines:,}")
    lines.append(f"  Functions:        {summary.functions}")
    lines.append(f"  Avg Func Length:  {summary.avg_function_length:.1f}")
    lines.append(f"  Max Func Length:  {summary.max_function_length}")
    lines.append(f"  Avg Complexity:   {summary.avg_complexity:.1f}")
    lines.append(f"  Max Complexity:   {summary.max_complexity}")
    lines.append(f"  Comment Ratio:   {summary.test_coverage:.1%}")
    lines.append("")

    # 按扩展名统计
    ext_counts = defaultdict(int)
    for r in details:
        ext_counts[r["ext"]] += 1

    lines.append("[File Types]")
    for ext, count in sorted(ext_counts.items(), key=lambda x: -x[1]):
        lines.append(f"  {ext}: {count} files")
    lines.append("")

    # Top 复杂文件
    lines.append("[Top Complex Files]")
    sorted_details = sorted(details, key=lambda x: x.get("complexity", 0), reverse=True)[:10]
    for r in sorted_details:
        lines.append(f"  {Path(r['file']).name}: complexity={r['complexity']}, lines={r['total_lines']}")
    lines.append("")

    lines.append("=" * 60)
    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser(
        description="DevFlow Code Quality Dashboard",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Generate report for current directory
  python dashboard.py --dir .

  # Generate JSON report
  python dashboard.py --dir . --format json

  # Generate HTML report
  python dashboard.py --dir . --output report.html

  # Show trend (requires historical data)
  python dashboard.py --trend --days 30
        """
    )

    parser.add_argument("--dir", "-d", default=".", help="Project directory")
    parser.add_argument("--format", "-f", choices=["text", "json", "html"], default="text", help="Output format")
    parser.add_argument("--output", "-o", help="Output file path")
    parser.add_argument("--trend", action="store_true", help="Show trend (requires history)")
    parser.add_argument("--days", type=int, default=30, help="Days for trend analysis")

    args = parser.parse_args()

    # 扫描目录
    print("Scanning directory...", file=sys.stderr)
    details = scan_directory(args.dir)

    if not details:
        print("No code files found.", file=sys.stderr)
        sys.exit(0)

    # 计算汇总
    summary = calculate_summary(details)

    # 生成报告
    if args.format == "html":
        report = generate_html_report(summary, details)
    else:
        report = format_report(summary, details, args.format)

    # 输出
    if args.output:
        Path(args.output).write_text(report, encoding="utf-8")
        print(f"Report saved to: {args.output}")
    else:
        print(report)


if __name__ == "__main__":
    main()
