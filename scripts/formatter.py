#!/usr/bin/env python3
"""
DevFlow - Code Formatter
统一代码风格
Usage:
  python formatter.py --dir src/
  python formatter.py --file main.py
  python formatter.py --dir src/ --check
  python formatter.py --dir src/ --fix
"""

import argparse
import json
import os
import re
import sys
from pathlib import Path
from typing import Dict, List, Tuple

# 支持的文件扩展名
SUPPORTED_EXTENSIONS = {
    ".py": "python",
    ".js": "javascript",
    ".ts": "typescript",
    ".jsx": "javascript",
    ".tsx": "typescript",
    ".json": "json",
    ".md": "markdown",
    ".html": "html",
    ".css": "css",
    ".yml": "yaml",
    ".yaml": "yaml"
}


def check_trailing_whitespace(line: str) -> bool:
    """检查行尾空格"""
    return line.rstrip() != line


def check_missing_newline_at_eof(content: str) -> bool:
    """检查文件末尾是否缺少换行符"""
    return content and not content.endswith("\n")


def check_indentation(line: str, indent_type: str = "spaces") -> Tuple[bool, str]:
    """检查缩进"""
    if not line.strip():
        return True, ""

    # 计算前导空格
    stripped = line.lstrip()
    indent = len(line) - len(stripped)

    if indent_type == "spaces":
        # 检查是否使用空格（而非 Tab）
        if "\t" in line[:indent]:
            return False, "Uses tabs instead of spaces"
        # 检查是否是 4 的倍数
        if indent % 4 != 0:
            return False, f"Indentation ({indent}) is not multiple of 4"
    elif indent_type == "tabs":
        # 检查是否使用 Tab
        if not line.startswith("\t"):
            return False, "Uses spaces instead of tabs"

    return True, ""


def check_line_length(line: str, max_length: int = 120) -> Tuple[bool, str]:
    """检查行长度"""
    if len(line) > max_length:
        return False, f"Line too long ({len(line)} > {max_length})"
    return True, ""


def check_blank_lines(content: str, ext: str) -> List[Dict]:
    """检查空行"""
    issues = []
    lines = content.split("\n")

    if ext == ".py":
        # Python: 顶层函数/类之间应该有 2 个空行
        prev_was_def = False
        blank_count = 0

        for i, line in enumerate(lines, 1):
            stripped = line.strip()

            if not stripped:
                blank_count += 1
                continue

            if stripped.startswith(("def ", "class ", "async def ")):
                if prev_was_def and blank_count < 2:
                    issues.append({
                        "line": i,
                        "message": "Expected 2 blank lines before function/class"
                    })
                prev_was_def = True
                blank_count = 0
            else:
                if not stripped.startswith(("#", "@", '"""', "'''")):
                    prev_was_def = False
                    blank_count = 0

    return issues


def check_imports(content: str, ext: str) -> List[Dict]:
    """检查导入语句"""
    issues = []
    lines = content.split("\n")

    if ext == ".py":
        import_section = []
        in_import = False

        for i, line in enumerate(lines, 1):
            stripped = line.strip()

            if stripped.startswith(("import ", "from ")):
                in_import = True
                import_section.append((i, stripped))
            elif in_import and not stripped.startswith(("#", "")):
                in_import = False

                # 检查导入顺序
                if len(import_section) > 1:
                    stdlib_imports = []
                    third_party_imports = []
                    local_imports = []

                    for _, imp in import_section:
                        if imp.startswith("from .") or imp.startswith("import ."):
                            local_imports.append(imp)
                        elif any(imp.startswith(f"import {m}") or imp.startswith(f"from {m}")
                                for m in ["os", "sys", "re", "json", "pathlib", "typing", "collections"]):
                            stdlib_imports.append(imp)
                        else:
                            third_party_imports.append(imp)

                    # 检查顺序
                    if local_imports and third_party_imports and stdlib_imports:
                        # 应该是: stdlib -> third_party -> local
                        pass  # 简化检查

                import_section = []

    return issues


def analyze_file(file_path: str) -> List[Dict]:
    """分析单个文件"""
    issues = []
    path = Path(file_path)
    ext = path.suffix

    if ext not in SUPPORTED_EXTENSIONS:
        return issues

    try:
        content = path.read_text(encoding="utf-8", errors="ignore")
        lines = content.split("\n")

        for i, line in enumerate(lines, 1):
            # 检查行尾空格
            if check_trailing_whitespace(line):
                issues.append({
                    "file": file_path,
                    "line": i,
                    "type": "trailing_whitespace",
                    "message": "Trailing whitespace"
                })

            # 检查行长度
            ok, msg = check_line_length(line)
            if not ok:
                issues.append({
                    "file": file_path,
                    "line": i,
                    "type": "line_length",
                    "message": msg
                })

            # 检查缩进
            if ext == ".py":
                ok, msg = check_indentation(line, "spaces")
                if not ok:
                    issues.append({
                        "file": file_path,
                        "line": i,
                        "type": "indentation",
                        "message": msg
                    })

        # 检查文件末尾换行
        if check_missing_newline_at_eof(content):
            issues.append({
                "file": file_path,
                "line": len(lines),
                "type": "newline_eof",
                "message": "Missing newline at end of file"
            })

        # 检查空行
        blank_issues = check_blank_lines(content, ext)
        for issue in blank_issues:
            issues.append({
                "file": file_path,
                **issue
            })

    except Exception as e:
        issues.append({
            "file": file_path,
            "line": 0,
            "type": "error",
            "message": str(e)
        })

    return issues


def fix_file(file_path: str) -> Tuple[int, int]:
    """修复文件"""
    path = Path(file_path)
    ext = path.suffix

    if ext not in SUPPORTED_EXTENSIONS:
        return 0, 0

    try:
        content = path.read_text(encoding="utf-8", errors="ignore")
        lines = content.split("\n")
        fixed_count = 0

        new_lines = []
        for line in lines:
            # 移除行尾空格
            new_line = line.rstrip()
            if new_line != line:
                fixed_count += 1
            new_lines.append(new_line)

        # 确保文件末尾有换行
        new_content = "\n".join(new_lines)
        if new_content and not new_content.endswith("\n"):
            new_content += "\n"
            fixed_count += 1

        # 写回文件
        path.write_text(new_content, encoding="utf-8")

        return fixed_count, len(lines)
    except Exception as e:
        print(f"Error fixing {file_path}: {e}", file=sys.stderr)
        return 0, 0


def scan_directory(directory: str) -> List[Dict]:
    """扫描目录"""
    all_issues = []
    dir_path = Path(directory)

    for file_path in dir_path.rglob("*"):
        # 跳过忽略的目录
        if any(part.startswith(".") or part in ("node_modules", "vendor", "dist", "build", "__pycache__")
               for part in file_path.parts):
            continue

        if file_path.suffix in SUPPORTED_EXTENSIONS and file_path.is_file():
            issues = analyze_file(str(file_path))
            all_issues.extend(issues)

    return all_issues


def fix_directory(directory: str) -> Tuple[int, int]:
    """修复目录"""
    total_fixed = 0
    total_files = 0
    dir_path = Path(directory)

    for file_path in dir_path.rglob("*"):
        # 跳过忽略的目录
        if any(part.startswith(".") or part in ("node_modules", "vendor", "dist", "build", "__pycache__")
               for part in file_path.parts):
            continue

        if file_path.suffix in SUPPORTED_EXTENSIONS and file_path.is_file():
            fixed, lines = fix_file(str(file_path))
            if fixed > 0:
                total_fixed += fixed
                total_files += 1
                print(f"Fixed {file_path}: {fixed} issues")

    return total_files, total_fixed


def format_report(issues: List[Dict], format: str = "text") -> str:
    """格式化报告"""
    if format == "json":
        return json.dumps({
            "total": len(issues),
            "by_type": {},
            "by_file": {},
            "issues": issues
        }, indent=2, ensure_ascii=False)

    lines = []
    lines.append("=" * 60)
    lines.append("DevFlow Code Formatter Report")
    lines.append("=" * 60)
    lines.append("")

    # 按类型统计
    by_type = {}
    for issue in issues:
        issue_type = issue.get("type", "unknown")
        by_type[issue_type] = by_type.get(issue_type, 0) + 1

    lines.append("[Summary]")
    lines.append(f"  Total issues: {len(issues)}")
    for issue_type, count in sorted(by_type.items()):
        lines.append(f"  - {issue_type}: {count}")
    lines.append("")

    # 按文件分组
    by_file = {}
    for issue in issues:
        file_path = issue.get("file", "")
        if file_path not in by_file:
            by_file[file_path] = []
        by_file[file_path].append(issue)

    if by_file:
        lines.append("[Issues by File]")
        lines.append("-" * 60)
        for file_path, file_issues in sorted(by_file.items()):
            lines.append(f"\n{Path(file_path).name} ({len(file_issues)} issues):")
            for issue in file_issues[:10]:
                lines.append(f"  L{issue.get('line', '?')}: {issue.get('message', '')}")
            if len(file_issues) > 10:
                lines.append(f"  ... and {len(file_issues) - 10} more")
        lines.append("")

    if not issues:
        lines.append("[OK] No formatting issues found!")

    lines.append("=" * 60)
    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser(
        description="DevFlow Code Formatter",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Check formatting
  python formatter.py --dir src/ --check

  # Fix formatting
  python formatter.py --dir src/ --fix

  # Check single file
  python formatter.py --file main.py --check

  # Output as JSON
  python formatter.py --dir src/ --format json
        """
    )

    parser.add_argument("--dir", "-d", help="Directory to check/fix")
    parser.add_argument("--file", "-f", help="Single file to check/fix")
    parser.add_argument("--check", action="store_true", help="Check formatting")
    parser.add_argument("--fix", action="store_true", help="Fix formatting")
    parser.add_argument("--format", choices=["text", "json"], default="text", help="Output format")
    parser.add_argument("--output", "-o", help="Output file path")

    args = parser.parse_args()

    if not args.dir and not args.file:
        print("Error: --dir or --file is required", file=sys.stderr)
        sys.exit(1)

    # 修复模式
    if args.fix:
        if args.file:
            fixed, total = fix_file(args.file)
            print(f"Fixed {fixed} issues in {args.file}")
        else:
            files, issues = fix_directory(args.dir)
            print(f"Fixed {issues} issues in {files} files")
        return

    # 检查模式
    if args.file:
        issues = analyze_file(args.file)
    else:
        issues = scan_directory(args.dir)

    # 生成报告
    report = format_report(issues, args.format)

    # 输出
    if args.output:
        Path(args.output).write_text(report, encoding="utf-8")
        print(f"Report saved to: {args.output}")
    else:
        print(report)

    # 返回状态码
    if issues:
        sys.exit(1)


if __name__ == "__main__":
    main()
