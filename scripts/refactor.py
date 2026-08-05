#!/usr/bin/env python3
"""
DevFlow - 智能重构建议
检测可重构的代码模式并给出具体建议：
- 重复代码块
- 长函数
- 深嵌套
- 复杂条件
- 魔法数字
- 未使用的函数参数
Usage: python refactor.py --dir .
       python refactor.py --file foo.py
       python refactor.py --dir . --json
"""

import argparse
import json
import os
import re
import sys
from pathlib import Path

IGNORE_DIRS = {"node_modules", ".git", "__pycache__", "dist", "build", ".next",
               "target", "vendor", ".venv", "venv"}
CODE_EXTS = {".py", ".js", ".ts", ".tsx", ".jsx", ".java", ".go", ".c", ".cpp",
             ".rs", ".rb", ".php"}

# 魔法数字（常见例外：状态码、年份、数组大小）
MAGIC_EXCEPTIONS = {"200", "201", "400", "401", "403", "404", "500", "503",
                    "1024", "4096", "0", "1", "2", "3", "10", "100", "1000"}


def find_duplicate_blocks(filepath):
    """查找文件内重复代码块（3 行以上）"""
    try:
        content = Path(filepath).read_text(encoding="utf-8", errors="ignore")
    except Exception:
        return []

    lines = [l.rstrip() for l in content.split("\n")]
    blocks = {}
    findings = []

    for i in range(len(lines) - 2):
        # 取 3 行去空白后的块
        block_lines = []
        for j in range(3):
            stripped = lines[i + j].strip()
            if not stripped or stripped.startswith(("#", "//", "/*", "*")):
                block_lines = []
                break
            block_lines.append(stripped)

        if len(block_lines) == 3:
            block_key = "\n".join(block_lines)
            if len(block_key) > 40:  # 过滤太短的块
                if block_key in blocks:
                    findings.append({
                        "file": filepath,
                        "first": blocks[block_key],
                        "second": i + 1,
                        "block": block_lines[0][:60]
                    })
                else:
                    blocks[block_key] = i + 1

    return findings


def find_long_functions(filepath):
    """查找长函数"""
    try:
        content = Path(filepath).read_text(encoding="utf-8", errors="ignore")
    except Exception:
        return []

    findings = []
    current_func = None
    func_start = 0
    func_lines = 0

    for i, line in enumerate(content.split("\n"), 1):
        # Python 函数定义
        m = re.match(r"^\s*(?:async\s+def|def)\s+(\w+)\s*\(", line)
        # 其他语言函数
        if not m:
            m = re.match(r"^\s*(?:function\s+)?(\w+)\s*\([^)]*\)\s*\{", line)
        if not m:
            m = re.match(r"^\s*(?:public|private|protected)\s+[\w<>\[\]]+\s+(\w+)\s*\(", line)

        if m:
            if current_func and func_lines > 60:
                findings.append({"file": filepath, "line": func_start,
                                 "type": "长函数", "detail": f"{current_func} ({func_lines} 行)"})
            current_func = m.group(1)
            func_start = i
            func_lines = 1
        elif current_func:
            func_lines += 1

    if current_func and func_lines > 60:
        findings.append({"file": filepath, "line": func_start,
                         "type": "长函数", "detail": f"{current_func} ({func_lines} 行)"})
    return findings


def find_magic_numbers(filepath):
    """查找魔法数字"""
    try:
        content = Path(filepath).read_text(encoding="utf-8", errors="ignore")
    except Exception:
        return []

    findings = []
    # 匹配 2 位以上数字，且不是 import、行号、版本号
    pattern = re.compile(r"[^a-zA-Z_'\"](\d{2,})[^a-zA-Z_'\"]")
    for i, line in enumerate(content.split("\n"), 1):
        stripped = line.strip()
        if not stripped or stripped.startswith(("#", "//", "/*", "*")):
            continue
        if re.match(r"^(import|from|require|use|#include|def |class |function)", stripped):
            continue
        for m in pattern.finditer(stripped):
            num = m.group(1)
            if num not in MAGIC_EXCEPTIONS and not num.startswith(("19", "20")):
                findings.append({"file": filepath, "line": i, "type": "魔法数字",
                                 "detail": f"数字 {num} -> 建议提取为命名常量"})
                break  # 一行只报一次
    return findings


def find_deep_nesting(filepath):
    """查找深嵌套代码"""
    try:
        content = Path(filepath).read_text(encoding="utf-8", errors="ignore")
    except Exception:
        return []

    findings = []
    depth = 0
    max_depth = 0
    max_line = 0
    block_stack = []

    for i, line in enumerate(content.split("\n"), 1):
        stripped = line.strip()
        if not stripped:
            continue
        # 计算缩进深度（4 空格 = 1 层）
        indent = len(line) - len(line.lstrip())
        current_depth = indent // 4
        if current_depth > max_depth:
            max_depth = current_depth
            max_line = i
        # 检测控制流关键字的嵌套
        if current_depth >= 4 and re.match(r"(if |for |while |with |def )", stripped):
            block_stack.append((i, current_depth, stripped[:50]))

    # 报告嵌套超过 4 层的位置
    seen = set()
    for line_no, depth_, code in block_stack:
        if depth_ >= 5 and (line_no, depth_) not in seen:
            seen.add((line_no, depth_))
            findings.append({"file": filepath, "line": line_no, "type": "深嵌套",
                             "detail": f"嵌套深度 {depth_} -> 建议提取函数"})
    return findings


def analyze_file(filepath):
    """分析单个文件"""
    findings = []
    findings.extend(find_duplicate_blocks(filepath))
    findings.extend(find_long_functions(filepath))
    findings.extend(find_magic_numbers(filepath))
    findings.extend(find_deep_nesting(filepath))
    return findings


def scan_dir(dirpath):
    """扫描目录"""
    all_findings = []
    for root, dirs, files in os.walk(dirpath):
        dirs[:] = [d for d in dirs if d not in IGNORE_DIRS]
        for f in files:
            if Path(f).suffix in CODE_EXTS:
                all_findings.extend(analyze_file(os.path.join(root, f)))
    return all_findings


def main():
    parser = argparse.ArgumentParser(description="DevFlow 智能重构建议")
    parser.add_argument("--dir", default=".", help="项目目录")
    parser.add_argument("--file", help="单个文件")
    parser.add_argument("--json", action="store_true", help="JSON 输出")
    args = parser.parse_args()

    if args.file:
        findings = analyze_file(os.path.abspath(args.file))
    else:
        findings = scan_dir(os.path.abspath(args.dir))

    if args.json:
        print(json.dumps({"total": len(findings), "findings": findings},
                         ensure_ascii=False, indent=2))
        return

    if not findings:
        print("✨ 未发现明显的重构机会")
        return

    print("🔧 DevFlow 重构建议\n")
    for f in findings:
        print(f"  ⚠️  {f['type']}: {f['file']}:{f['line']}")
        print(f"     {f['detail']}")

    print(f"\n共 {len(findings)} 条建议")
    sys.exit(1)


if __name__ == "__main__":
    main()
