#!/usr/bin/env python3
"""
DevFlow - Code Heatmap
可视化代码复杂度
Usage:
  python heatmap.py --dir src/
  python heatmap.py --file main.py
  python heatmap.py --dir src/ --metric complexity
  python heatmap.py --dir src/ --output heatmap.html
"""

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Dict, List, Tuple
from collections import defaultdict


def calculate_complexity(content: str) -> int:
    """计算圈复杂度"""
    complexity = 1

    patterns = [
        r"\bif\b", r"\belse\b", r"\belif\b", r"\bfor\b", r"\bwhile\b",
        r"\bcase\b", r"\bcatch\b", r"\btry\b", r"\bexcept\b", r"\bfinally\b",
        r"&&", r"\|\|", r"\?", r"and\b", r"or\b"
    ]

    for pattern in patterns:
        complexity += len(re.findall(pattern, content))

    return complexity


def calculate_cognitive_complexity(content: str) -> int:
    """计算认知复杂度"""
    complexity = 0
    nesting = 0

    for line in content.split("\n"):
        stripped = line.strip()

        # 跳过注释和空行
        if not stripped or stripped.startswith(("#", "//", "/*", "*")):
            continue

        # 计算缩进级别
        indent = len(line) - len(line.lstrip())
        current_nesting = indent // 4

        # 控制流增加复杂度
        if re.match(r"^(if|elif|else|for|while|try|except|finally|case|switch)", stripped):
            complexity += 1 + abs(current_nesting - nesting)
            nesting = current_nesting

        # 逻辑运算符
        complexity += len(re.findall(r"&&|\|\||and|or", stripped))

        # 嵌套深度
        if current_nesting > nesting:
            complexity += current_nesting - nesting

    return complexity


def calculate_maintainability(content: str) -> float:
    """计算可维护性指数 (0-100)"""
    lines = content.split("\n")
    total_lines = len(lines)

    if total_lines == 0:
        return 100.0

    # 代码行数
    code_lines = sum(1 for l in lines if l.strip() and not l.strip().startswith(("#", "//", "/*", "*")))

    # 注释行数
    comment_lines = sum(1 for l in lines if l.strip().startswith(("#", "//", "/*", "*")))

    # 复杂度
    complexity = calculate_complexity(content)

    # 函数数量
    func_count = len(re.findall(r"^(?:def|function|func|public|private|protected)\s+\w+", content, re.MULTILINE))

    # 平均函数长度
    avg_func_len = code_lines / max(func_count, 1)

    # 计算可维护性指数
    # 简化公式：100 - 复杂度惩罚 - 长度惩罚 + 注释奖励
    maintainability = 100.0
    maintainability -= min(complexity * 2, 40)  # 复杂度惩罚
    maintainability -= min(avg_func_len / 5, 20)  # 函数长度惩罚
    maintainability += min(comment_lines / code_lines * 20, 20) if code_lines > 0 else 0  # 注释奖励

    return max(0, min(100, maintainability))


def analyze_file(file_path: str) -> Dict:
    """分析单个文件"""
    try:
        content = Path(file_path).read_text(encoding="utf-8", errors="ignore")
        lines = content.split("\n")

        complexity = calculate_complexity(content)
        cognitive = calculate_cognitive_complexity(content)
        maintainability = calculate_maintainability(content)

        # 统计
        code_lines = sum(1 for l in lines if l.strip() and not l.strip().startswith(("#", "//", "/*", "*")))
        comment_lines = sum(1 for l in lines if l.strip().startswith(("#", "//", "/*", "*")))
        blank_lines = sum(1 for l in lines if not l.strip())

        # 函数列表
        functions = []
        for i, line in enumerate(lines, 1):
            match = re.match(r"^(?:def|function|func|public|private|protected)\s+(\w+)", line)
            if match:
                functions.append({
                    "name": match.group(1),
                    "line": i
                })

        return {
            "file": file_path,
            "lines": len(lines),
            "code_lines": code_lines,
            "comment_lines": comment_lines,
            "blank_lines": blank_lines,
            "complexity": complexity,
            "cognitive_complexity": cognitive,
            "maintainability": maintainability,
            "functions": len(functions),
            "func_list": functions
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

        if file_path.suffix in (".py", ".js", ".ts", ".jsx", ".tsx", ".java", ".go", ".rs") and file_path.is_file():
            result = analyze_file(str(file_path))
            if "error" not in result:
                results.append(result)

    return results


def generate_html_heatmap(results: List[Dict], metric: str = "complexity") -> str:
    """生成 HTML 热力图"""
    # 按指标排序
    if metric == "complexity":
        sorted_results = sorted(results, key=lambda x: x.get("complexity", 0), reverse=True)
        title = "Code Complexity Heatmap"
        max_val = max(r.get("complexity", 0) for r in results) if results else 1
    elif metric == "maintainability":
        sorted_results = sorted(results, key=lambda x: x.get("maintainability", 100))
        title = "Maintainability Heatmap"
        max_val = 100
    else:
        sorted_results = results
        title = "Code Lines Heatmap"
        max_val = max(r.get("code_lines", 0) for r in results) if results else 1

    html = f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{title}</title>
    <style>
        body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; margin: 20px; background: #f5f5f5; }}
        .container {{ max-width: 1200px; margin: 0 auto; }}
        h1 {{ color: #333; }}
        .heatmap {{ display: grid; grid-template-columns: repeat(auto-fill, minmax(100px, 1fr)); gap: 10px; margin: 20px 0; }}
        .cell {{ padding: 15px; border-radius: 8px; text-align: center; color: white; font-weight: bold; cursor: pointer; transition: transform 0.2s; }}
        .cell:hover {{ transform: scale(1.05); }}
        .legend {{ display: flex; gap: 10px; margin: 20px 0; }}
        .legend-item {{ padding: 5px 15px; border-radius: 4px; color: white; }}
        .info {{ background: white; padding: 20px; border-radius: 10px; box-shadow: 0 2px 10px rgba(0,0,0,0.1); margin: 20px 0; }}
    </style>
</head>
<body>
    <div class="container">
        <h1>{title}</h1>
        <p>Generated by DevFlow | Metric: {metric}</p>

        <div class="legend">
            <div class="legend-item" style="background: #28a745;">Low</div>
            <div class="legend-item" style="background: #ffc107;">Medium</div>
            <div class="legend-item" style="background: #dc3545;">High</div>
        </div>

        <div class="heatmap">
"""

    for result in sorted_results[:50]:
        file_name = Path(result["file"]).name

        if metric == "complexity":
            value = result.get("complexity", 0)
            normalized = min(value / max_val, 1) if max_val > 0 else 0
        elif metric == "maintainability":
            value = result.get("maintainability", 100)
            normalized = 1 - (value / 100)  # 反转：低可维护性 = 高风险
        else:
            value = result.get("code_lines", 0)
            normalized = min(value / max_val, 1) if max_val > 0 else 0

        # 颜色计算
        if normalized < 0.33:
            color = "#28a745"  # 绿色
        elif normalized < 0.66:
            color = "#ffc107"  # 黄色
        else:
            color = "#dc3545"  # 红色

        html += f"""
            <div class="cell" style="background: {color};" title="{file_name}: {value}">
                <div style="font-size: 12px; overflow: hidden; text-overflow: ellipsis;">{file_name}</div>
                <div style="font-size: 18px; margin-top: 5px;">{value}</div>
            </div>
"""

    html += """
        </div>

        <div class="info">
            <h2>Summary</h2>
"""

    # 统计信息
    total_files = len(results)
    total_lines = sum(r.get("lines", 0) for r in results)
    avg_complexity = sum(r.get("complexity", 0) for r in results) / total_files if total_files > 0 else 0
    avg_maintainability = sum(r.get("maintainability", 0) for r in results) / total_files if total_files > 0 else 0

    html += f"""
            <p>Total Files: {total_files}</p>
            <p>Total Lines: {total_lines:,}</p>
            <p>Average Complexity: {avg_complexity:.1f}</p>
            <p>Average Maintainability: {avg_maintainability:.1f}%</p>
        </div>
    </div>
</body>
</html>
"""

    return html


def format_report(results: List[Dict], metric: str, format: str = "text") -> str:
    """格式化报告"""
    if format == "json":
        return json.dumps({
            "total": len(results),
            "metric": metric,
            "files": results
        }, indent=2, ensure_ascii=False)

    if format == "html":
        return generate_html_heatmap(results, metric)

    # 文本格式
    lines = []
    lines.append("=" * 60)
    lines.append("DevFlow Code Heatmap")
    lines.append("=" * 60)
    lines.append(f"Metric: {metric}")
    lines.append("")

    # 排序
    if metric == "complexity":
        sorted_results = sorted(results, key=lambda x: x.get("complexity", 0), reverse=True)
    elif metric == "maintainability":
        sorted_results = sorted(results, key=lambda x: x.get("maintainability", 100))
    else:
        sorted_results = sorted(results, key=lambda x: x.get("code_lines", 0), reverse=True)

    lines.append("[Top Files]")
    lines.append("-" * 60)

    for result in sorted_results[:20]:
        file_name = Path(result["file"]).name
        complexity = result.get("complexity", 0)
        maintainability = result.get("maintainability", 0)
        lines.append(f"  {file_name}: complexity={complexity}, maintainability={maintainability:.1f}%")

    lines.append("")

    # 统计
    total_files = len(results)
    avg_complexity = sum(r.get("complexity", 0) for r in results) / total_files if total_files > 0 else 0
    avg_maintainability = sum(r.get("maintainability", 0) for r in results) / total_files if total_files > 0 else 0

    lines.append("[Summary]")
    lines.append(f"  Total Files: {total_files}")
    lines.append(f"  Average Complexity: {avg_complexity:.1f}")
    lines.append(f"  Average Maintainability: {avg_maintainability:.1f}%")
    lines.append("=" * 60)

    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser(
        description="DevFlow Code Heatmap",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Generate complexity heatmap
  python heatmap.py --dir src/

  # Generate maintainability heatmap
  python heatmap.py --dir src/ --metric maintainability

  # Generate HTML report
  python heatmap.py --dir src/ --output heatmap.html

  # Analyze single file
  python heatmap.py --file main.py
        """
    )

    parser.add_argument("--dir", "-d", help="Directory to scan")
    parser.add_argument("--file", "-f", help="Single file to analyze")
    parser.add_argument("--metric", "-m", choices=["complexity", "maintainability", "lines"],
                        default="complexity", help="Metric to visualize")
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
    report = format_report(results, args.metric, args.format)

    # 输出
    if args.output:
        Path(args.output).write_text(report, encoding="utf-8")
        print(f"Heatmap saved to: {args.output}")
    else:
        print(report)


if __name__ == "__main__":
    main()
