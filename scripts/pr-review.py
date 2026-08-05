#!/usr/bin/env python3
"""
DevFlow - PR Review Tool
支持 GitHub/GitLab PR 自动审查
Usage:
  python pr-review.py --repo owner/repo --number 123
  python pr-review.py --repo owner/repo --number 123 --mode security
  python pr-review.py --file diff.txt --mode all
"""

import argparse
import json
import os
import re
import sys
from pathlib import Path
from typing import Dict, List, Optional

# 安全模式
SECURITY_PATTERNS = [
    (r"eval\(", "L4", "eval() 存在代码注入风险"),
    (r"exec\(", "L4", "exec() 存在代码注入风险"),
    (r"os\.system\(", "L4", "os.system() 存在命令注入风险"),
    (r"subprocess\.call\(.*shell\s*=\s*True", "L4", "shell=True 存在命令注入风险"),
    (r"innerHTML\s*=", "L4", "innerHTML 存在 XSS 风险"),
    (r"dangerouslySetInnerHTML", "L4", "dangerouslySetInnerHTML 存在 XSS 风险"),
    (r"password\s*=\s*[\x27\x22][^\x27\x22]+[\x27\x22]", "L4", "硬编码密码"),
    (r"api[_-]?key\s*=\s*[\x27\x22][^\x27\x22]+[\x27\x22]", "L4", "硬编码 API Key"),
    (r"secret\s*=\s*[\x27\x22][^\x27\x22]+[\x27\x22]", "L4", "硬编码 Secret"),
    (r"\.md5\(|\.sha1\(", "L4", "使用弱加密算法"),
    (r"SELECT\s+.*\s+FROM\s+.*\s+WHERE\s+.*\+", "L4", "SQL 拼接，存在注入风险"),
]

# 逻辑模式
LOGIC_PATTERNS = [
    (r"except\s*:\s*pass", "L2", "空异常捕获，吞掉错误"),
    (r"catch\s*\(\s*\w+\s*\)\s*\{[\s\n]*\}", "L2", "空 catch 块"),
    (r"==\s*None|!=\s*None", "L2", "建议使用 is None / is not None"),
    (r"==\s*True|==\s*False", "L2", "直接比较布尔值"),
    (r"for\s+.*\n\s*for\s+.*\n\s*for\s+", "L2", "三层嵌套循环，考虑重构"),
]

# 性能模式
PERF_PATTERNS = [
    (r"\.forEach.*\.query|\.map.*\.query", "L3", "循环中查询数据库，N+1 问题"),
    (r"JSON\.parse\(JSON\.stringify", "L3", "深拷贝效率低，建议 structuredClone()"),
    (r"\.concat\(", "L3", "数组拼接效率低，建议展开运算符"),
    (r"import\s+\*", "L3", "通配符导入，影响 Tree Shaking"),
    (r"sleep\(\d+\)", "L3", "阻塞式 sleep，考虑异步方案"),
]

# 代码风格模式
STYLE_PATTERNS = [
    (r"console\.log\(", "L3", "生产代码包含 console.log"),
    (r"print\(", "L3", "生产代码包含 print 语句"),
    (r"debugger;", "L3", "生产代码包含 debugger"),
    (r"TODO:|FIXME:|HACK:", "L3", "存在未完成的 TODO/FIXME"),
]


def parse_diff(diff_content: str) -> Dict[str, List[str]]:
    """解析 diff 内容，提取文件和变更行"""
    files = {}
    current_file = None
    added_lines = []

    for line in diff_content.split("\n"):
        # 匹配文件头
        if line.startswith("+++ b/") or line.startswith("--- a/"):
            continue
        if line.startswith("diff --git"):
            if current_file and added_lines:
                files[current_file] = added_lines
            # 提取文件名
            match = re.search(r"b/(.+)$", line)
            if match:
                current_file = match.group(1)
                added_lines = []
        elif line.startswith("+") and not line.startswith("+++"):
            added_lines.append(line[1:])

    if current_file and added_lines:
        files[current_file] = added_lines

    return files


def scan_code(lines: List[str], patterns: List[tuple], file_path: str = "") -> List[Dict]:
    """扫描代码行，返回问题列表"""
    results = []

    for i, line in enumerate(lines, 1):
        for pattern, level, message in patterns:
            if re.search(pattern, line, re.IGNORECASE):
                # 跳过注释行
                stripped = line.strip()
                if stripped.startswith(("//", "#", "/*", "*", "<!--")):
                    continue
                # 跳过忽略标记
                if "devflow-ignore" in line or "noqa" in line or "eslint-disable" in line:
                    continue

                results.append({
                    "file": file_path,
                    "line": i,
                    "level": level,
                    "message": message,
                    "code": stripped[:100]
                })

    return results


def review_diff(diff_content: str, mode: str = "all") -> Dict:
    """审查 diff 内容"""
    files = parse_diff(diff_content)
    all_issues = []

    for file_path, lines in files.items():
        # 跳过非代码文件
        ext = Path(file_path).suffix
        if ext not in (".py", ".js", ".ts", ".jsx", ".tsx", ".java", ".go", ".rs", ".c", ".cpp", ".rb", ".php"):
            continue

        issues = []

        if mode in ("all", "security"):
            issues.extend(scan_code(lines, SECURITY_PATTERNS, file_path))

        if mode in ("all", "logic"):
            issues.extend(scan_code(lines, LOGIC_PATTERNS, file_path))

        if mode in ("all", "performance"):
            issues.extend(scan_code(lines, PERF_PATTERNS, file_path))

        if mode in ("all", "style"):
            issues.extend(scan_code(lines, STYLE_PATTERNS, file_path))

        all_issues.extend(issues)

    return {
        "total_files": len(files),
        "total_lines": sum(len(lines) for lines in files.values()),
        "issues": all_issues,
        "summary": generate_summary(all_issues)
    }


def generate_summary(issues: List[Dict]) -> Dict:
    """生成审查摘要"""
    summary = {
        "total": len(issues),
        "critical": 0,
        "warning": 0,
        "info": 0,
        "by_category": {}
    }

    for issue in issues:
        level = issue["level"]
        if level == "L4":
            summary["critical"] += 1
        elif level in ("L2", "L3"):
            summary["warning"] += 1
        else:
            summary["info"] += 1

        # 按类别统计
        category = issue["message"].split("，")[0] if "，" in issue["message"] else issue["message"][:20]
        summary["by_category"][category] = summary["by_category"].get(category, 0) + 1

    return summary


def format_report(review_result: Dict, format: str = "text") -> str:
    """格式化审查报告"""
    if format == "json":
        return json.dumps(review_result, ensure_ascii=False, indent=2)

    lines = []
    lines.append("=" * 60)
    lines.append("DevFlow PR Review Report")
    lines.append("=" * 60)
    lines.append("")

    summary = review_result["summary"]
    lines.append("[Summary]")
    lines.append(f"  - Files reviewed: {review_result['total_files']}")
    lines.append(f"  - Lines added: {review_result['total_lines']}")
    lines.append(f"  - Issues found: {summary['total']}")
    lines.append(f"    - [CRITICAL] Critical: {summary['critical']}")
    lines.append(f"    - [WARNING] Warning: {summary['warning']}")
    lines.append(f"    - [INFO] Info: {summary['info']}")
    lines.append("")

    if review_result["issues"]:
        lines.append("[Issues]")
        lines.append("-" * 60)

        for issue in review_result["issues"]:
            level_icon = {"L1": "[E]", "L2": "[W]", "L3": "[I]", "L4": "[C]"}.get(issue["level"], "[?]")
            lines.append(f"{level_icon} [{issue['level']}] {issue['file']}:{issue['line']}")
            lines.append(f"   {issue['message']}")
            lines.append(f"   Code: {issue['code']}")
            lines.append("")
    else:
        lines.append("[OK] No issues found!")

    lines.append("=" * 60)
    return "\n".join(lines)


def read_diff_from_file(file_path: str) -> str:
    """从文件读取 diff 内容"""
    try:
        return Path(file_path).read_text(encoding="utf-8")
    except Exception as e:
        print(f"Error reading file: {e}", file=sys.stderr)
        sys.exit(1)


def read_diff_from_stdin() -> str:
    """从标准输入读取 diff 内容"""
    if sys.stdin.isatty():
        print("Reading from stdin... (Ctrl+D to end)", file=sys.stderr)
    return sys.stdin.read()


def main():
    parser = argparse.ArgumentParser(
        description="DevFlow PR Review Tool",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Review diff from file
  python pr-review.py --file diff.txt

  # Review diff from stdin
  git diff | python pr-review.py

  # Review with specific mode
  python pr-review.py --file diff.txt --mode security

  # Output as JSON
  python pr-review.py --file diff.txt --format json
        """
    )

    parser.add_argument("--file", "-f", help="Diff file path")
    parser.add_argument("--mode", "-m", choices=["all", "security", "logic", "performance", "style"],
                        default="all", help="Review mode (default: all)")
    parser.add_argument("--format", choices=["text", "json"], default="text", help="Output format")
    parser.add_argument("--output", "-o", help="Output file path")

    args = parser.parse_args()

    # 获取 diff 内容
    if args.file:
        diff_content = read_diff_from_file(args.file)
    else:
        diff_content = read_diff_from_stdin()

    if not diff_content.strip():
        print("No diff content provided.", file=sys.stderr)
        sys.exit(1)

    # 执行审查
    result = review_diff(diff_content, args.mode)

    # 格式化输出
    report = format_report(result, args.format)

    # 输出结果
    if args.output:
        Path(args.output).write_text(report, encoding="utf-8")
        print(f"Report saved to: {args.output}")
    else:
        print(report)

    # 返回状态码
    if result["summary"]["critical"] > 0:
        sys.exit(1)  # 有严重问题
    elif result["summary"]["warning"] > 0:
        sys.exit(1)  # 有警告
    else:
        sys.exit(0)  # 无问题


if __name__ == "__main__":
    main()
