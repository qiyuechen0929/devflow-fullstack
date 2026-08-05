#!/usr/bin/env python3
"""
DevFlow - Performance Profiler
代码性能分析
Usage:
  python profiler.py --file main.py
  python profiler.py --file main.py --function my_func
  python profiler.py --dir src/
  python profiler.py --file main.py --output report.html
"""

import argparse
import json
import re
import sys
import time
from pathlib import Path
from typing import Dict, List, Optional, Tuple


def analyze_algorithm_complexity(content: str) -> Dict:
    """分析算法复杂度"""
    lines = content.split("\n")

    # 检测循环嵌套
    max_nesting = 0
    current_nesting = 0
    loop_lines = []

    for i, line in enumerate(lines, 1):
        stripped = line.strip()

        # 检测循环
        if re.match(r"^(for|while)\b", stripped):
            current_nesting += 1
            if current_nesting > max_nesting:
                max_nesting = current_nesting
            loop_lines.append({"line": i, "nesting": current_nesting, "code": stripped})

        # 检测函数结束（简化）
        if stripped == "" and current_nesting > 0:
            current_nesting = max(0, current_nesting - 1)

    # 估算时间复杂度
    if max_nesting >= 3:
        time_complexity = "O(n^3) or higher"
        severity = "critical"
    elif max_nesting == 2:
        time_complexity = "O(n^2)"
        severity = "warning"
    elif max_nesting == 1:
        time_complexity = "O(n)"
        severity = "ok"
    else:
        time_complexity = "O(1)"
        severity = "ok"

    # 检测常见性能问题
    issues = []

    # 检测循环中的数据库查询
    for i, line in enumerate(lines, 1):
        if re.search(r"\.query\(|\.execute\(|\.find\(|\.findOne\(", line):
            # 检查是否在循环中
            for loop in loop_lines:
                if i > loop["line"] and i < loop["line"] + 50:
                    issues.append({
                        "line": i,
                        "type": "n_plus_1",
                        "severity": "critical",
                        "message": "Database query inside loop - N+1 problem"
                    })

    # 检测不必要的深拷贝
    for i, line in enumerate(lines, 1):
        if "JSON.parse(JSON.stringify" in line:
            issues.append({
                "line": i,
                "type": "deep_copy",
                "severity": "warning",
                "message": "Inefficient deep copy - use structuredClone() or lodash.cloneDeep()"
            })

    # 检测同步阻塞
    for i, line in enumerate(lines, 1):
        if re.search(r"\.sleep\(|\.wait\(|\.readFileSync\(|\.writeFileSync\(", line):
            issues.append({
                "line": i,
                "type": "blocking",
                "severity": "warning",
                "message": "Synchronous blocking operation"
            })

    # 检测内存泄漏风险
    for i, line in enumerate(lines, 1):
        if re.search(r"addEventListener|setInterval|setTimeout", line):
            # 检查是否有对应的移除
            has_remove = any(re.search(r"removeEventListener|clearInterval|clearTimeout", l) for l in lines[i:i+50])
            if not has_remove:
                issues.append({
                    "line": i,
                    "type": "memory_leak",
                    "severity": "warning",
                    "message": "Potential memory leak - missing cleanup"
                })

    return {
        "max_nesting": max_nesting,
        "time_complexity": time_complexity,
        "severity": severity,
        "loop_lines": loop_lines,
        "issues": issues
    }


def analyze_memory_usage(content: str) -> Dict:
    """分析内存使用"""
    lines = content.split("\n")
    issues = []

    # 检测大数组/列表创建
    for i, line in enumerate(lines, 1):
        if re.search(r"\[\s*\]\s*\*\s*\d{4,}|range\(\d{6,}\)", line):
            issues.append({
                "line": i,
                "type": "large_allocation",
                "severity": "warning",
                "message": "Large memory allocation"
            })

    # 检测无限增长的数据结构
    for i, line in enumerate(lines, 1):
        if re.search(r"\.append\(|\.push\(|\.add\(", line):
            # 检查是否有清理逻辑
            has_cleanup = any(re.search(r"\.clear\(|\.remove\(|\.pop\(|= \[\]", l) for l in lines[max(0,i-20):i])
            if not has_cleanup:
                issues.append({
                    "line": i,
                    "type": "unbounded_growth",
                    "severity": "info",
                    "message": "Potential unbounded data structure growth"
                })

    return {
        "issues": issues
    }


def analyze_io_operations(content: str) -> Dict:
    """分析 I/O 操作"""
    lines = content.split("\n")
    issues = []

    # 检测文件操作
    for i, line in enumerate(lines, 1):
        if re.search(r"open\(|readFile|writeFile|fopen|fwrite", line):
            # 检查是否使用了 with 语句
            if "with " not in line and "using " not in line:
                issues.append({
                    "line": i,
                    "type": "file_handle",
                    "severity": "warning",
                    "message": "File operation without proper resource management"
                })

    # 检测网络请求
    for i, line in enumerate(lines, 1):
        if re.search(r"requests\.get|fetch\(|axios\.|http\.get|urllib", line):
            issues.append({
                "line": i,
                "type": "network_request",
                "severity": "info",
                "message": "Network request - consider caching or batching"
            })

    return {
        "issues": issues
    }


def analyze_file(file_path: str) -> Dict:
    """分析单个文件"""
    try:
        content = Path(file_path).read_text(encoding="utf-8", errors="ignore")
        lines = content.split("\n")

        # 分析算法复杂度
        algo_analysis = analyze_algorithm_complexity(content)

        # 分析内存使用
        memory_analysis = analyze_memory_usage(content)

        # 分析 I/O 操作
        io_analysis = analyze_io_operations(content)

        # 统计
        code_lines = sum(1 for l in lines if l.strip() and not l.strip().startswith(("#", "//", "/*", "*")))

        return {
            "file": file_path,
            "lines": len(lines),
            "code_lines": code_lines,
            "algorithm": algo_analysis,
            "memory": memory_analysis,
            "io": io_analysis,
            "total_issues": len(algo_analysis["issues"]) + len(memory_analysis["issues"]) + len(io_analysis["issues"])
        }
    except Exception as e:
        return {"file": file_path, "error": str(e)}


def scan_directory(directory: str) -> List[Dict]:
    """扫描目录"""
    results = []
    dir_path = Path(directory)

    for file_path in dir_path.rglob("*"):
        if any(part.startswith(".") or part in ("node_modules", "vendor", "dist", "build", "__pycache__")
               for part in file_path.parts):
            continue

        if file_path.suffix in (".py", ".js", ".ts", ".jsx", ".tsx", ".java", ".go") and file_path.is_file():
            result = analyze_file(str(file_path))
            if "error" not in result:
                results.append(result)

    return results


def generate_html_report(results: List[Dict]) -> str:
    """生成 HTML 报告"""
    total_files = len(results)
    total_issues = sum(r.get("total_issues", 0) for r in results)

    # 按严重性统计
    critical = sum(len([i for i in r.get("algorithm", {}).get("issues", []) if i.get("severity") == "critical"])
                   for r in results)
    warnings = sum(len([i for i in r.get("algorithm", {}).get("issues", []) if i.get("severity") == "warning"])
                   for r in results)

    html = f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>DevFlow Performance Profiler</title>
    <style>
        body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; margin: 20px; background: #f5f5f5; }}
        .container {{ max-width: 1200px; margin: 0 auto; }}
        h1 {{ color: #333; }}
        .cards {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 15px; margin: 20px 0; }}
        .card {{ background: white; padding: 20px; border-radius: 10px; box-shadow: 0 2px 10px rgba(0,0,0,0.1); }}
        .card h3 {{ margin: 0 0 10px 0; color: #666; font-size: 14px; }}
        .card .value {{ font-size: 32px; font-weight: bold; }}
        .critical {{ color: #dc3545; }}
        .warning {{ color: #ffc107; }}
        .ok {{ color: #28a745; }}
        .issue {{ background: white; padding: 15px; margin: 10px 0; border-radius: 8px; border-left: 4px solid #ddd; }}
        .issue.critical {{ border-left-color: #dc3545; }}
        .issue.warning {{ border-left-color: #ffc107; }}
        .issue.info {{ border-left-color: #17a2b8; }}
    </style>
</head>
<body>
    <div class="container">
        <h1>DevFlow Performance Profiler</h1>

        <div class="cards">
            <div class="card">
                <h3>Files Analyzed</h3>
                <div class="value">{total_files}</div>
            </div>
            <div class="card">
                <h3>Total Issues</h3>
                <div class="value {'critical' if critical > 0 else 'warning' if warnings > 0 else 'ok'}">{total_issues}</div>
            </div>
            <div class="card">
                <h3>Critical</h3>
                <div class="value critical">{critical}</div>
            </div>
            <div class="card">
                <h3>Warnings</h3>
                <div class="value warning">{warnings}</div>
            </div>
        </div>

        <h2>Issues Found</h2>
"""

    # 列出所有问题
    for result in results:
        file_name = Path(result["file"]).name
        issues = result.get("algorithm", {}).get("issues", []) + \
                 result.get("memory", {}).get("issues", []) + \
                 result.get("io", {}).get("issues", [])

        for issue in issues:
            severity = issue.get("severity", "info")
            html += f"""
        <div class="issue {severity}">
            <strong>{file_name}:{issue.get('line', '?')}</strong> - {issue.get('message', '')}
            <br><small>Type: {issue.get('type', 'unknown')}</small>
        </div>
"""

    html += """
    </div>
</body>
</html>
"""

    return html


def format_report(results: List[Dict], format: str = "text") -> str:
    """格式化报告"""
    if format == "json":
        return json.dumps({
            "total_files": len(results),
            "files": results
        }, indent=2, ensure_ascii=False)

    if format == "html":
        return generate_html_report(results)

    # 文本格式
    lines = []
    lines.append("=" * 60)
    lines.append("DevFlow Performance Profiler")
    lines.append("=" * 60)
    lines.append("")
    lines.append(f"Files analyzed: {len(results)}")
    lines.append("")

    total_critical = 0
    total_warning = 0

    for result in results:
        file_name = Path(result["file"]).name
        algo = result.get("algorithm", {})

        lines.append(f"[{file_name}]")
        lines.append(f"  Time Complexity: {algo.get('time_complexity', 'N/A')}")
        lines.append(f"  Max Nesting: {algo.get('max_nesting', 0)}")

        issues = algo.get("issues", []) + result.get("memory", {}).get("issues", []) + result.get("io", {}).get("issues", [])

        if issues:
            lines.append(f"  Issues: {len(issues)}")
            for issue in issues[:5]:
                severity_icon = {"critical": "[C]", "warning": "[W]", "info": "[I]"}.get(issue.get("severity"), "[?]")
                lines.append(f"    {severity_icon} L{issue.get('line', '?')}: {issue.get('message', '')}")

                if issue.get("severity") == "critical":
                    total_critical += 1
                elif issue.get("severity") == "warning":
                    total_warning += 1

        lines.append("")

    lines.append("[Summary]")
    lines.append(f"  Critical: {total_critical}")
    lines.append(f"  Warnings: {total_warning}")
    lines.append("=" * 60)

    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser(
        description="DevFlow Performance Profiler",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Analyze single file
  python profiler.py --file main.py

  # Analyze directory
  python profiler.py --dir src/

  # Generate HTML report
  python profiler.py --dir src/ --output report.html

  # Output as JSON
  python profiler.py --file main.py --format json
        """
    )

    parser.add_argument("--dir", "-d", help="Directory to scan")
    parser.add_argument("--file", "-f", help="Single file to analyze")
    parser.add_argument("--format", choices=["text", "json", "html"], default="text", help="Output format")
    parser.add_argument("--output", "-o", help="Output file path")

    args = parser.parse_args()

    if not args.dir and not args.file:
        print("Error: --dir or --file is required", file=sys.stderr)
        sys.exit(1)

    # 分析
    if args.file:
        result = analyze_file(args.file)
        results = [result]
    else:
        results = scan_directory(args.dir)

    if not results:
        print("No files found.", file=sys.stderr)
        sys.exit(0)

    # 生成报告
    report = format_report(results, args.format)

    # 输出
    if args.output:
        Path(args.output).write_text(report, encoding="utf-8")
        print(f"Report saved to: {args.output}")
    else:
        print(report)


if __name__ == "__main__":
    main()
