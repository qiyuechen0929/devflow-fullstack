#!/usr/bin/env python3
"""
DevFlow - 代码复杂度分析器
计算每个函数的圈复杂度（Cyclomatic Complexity）和代码行数
Usage: python complexity.py --file foo.py
       python complexity.py --dir src/
       python complexity.py --file foo.py --threshold 10
"""

import argparse
import json
import os
import re
from pathlib import Path

# 可分析的扩展名
EXTENSIONS = {".py", ".js", ".ts", ".tsx", ".jsx", ".java", ".go", ".c", ".cpp",
              ".rs", ".rb", ".php"}
IGNORE_DIRS = {"node_modules", ".git", "__pycache__", "dist", "build", ".next",
               "target", "vendor", ".venv", "venv"}

# 增加圈复杂度的关键字
COMPLEXITY_KEYWORDS = [
    r"\bif\b", r"\belse\b", r"\bfor\b", r"\bwhile\b", r"\bcase\b",
    r"\bcatch\b", r"\b&&\b", r"\b\|\|\b", r"\?.*:", r"\bdo\b",
    # Python 特有
    r"\belif\b", r"\bexcept\b", r"\bwith\b", r"\btry\b",
]

COMPILED_KEYWORDS = [re.compile(k) for k in COMPLEXITY_KEYWORDS]

# 函数/方法定义匹配（按语言）
FUNC_PATTERNS = [
    re.compile(r"^\s*(?:def|async\s+def)\s+(\w+)\s*\("),                      # Python
    re.compile(r"^\s*(?:function\s+)?(\w+)\s*\([^)]*\)\s*\{"),                # JS/TS/C/Java
    re.compile(r"^\s*(?:public|private|protected|internal)\s+[\w<>\[\]]+\s+(\w+)\s*\("),  # Java/C#
    re.compile(r"^\s*(?:func)\s+(\w+)\s*\("),                                 # Go
    re.compile(r"^\s*(?:def)\s+(\w+)\s*(?:\([^)]*\))?$"),                     # Ruby
    re.compile(r"^\s*(?:sub)\s+(\w+)"),                                       # Perl
    re.compile(r"^\s*(?:public|private|protected)\s+function\s+(\w+)\s*\("),  # PHP
]


def strip_comments(content):
    """去除注释，避免影响复杂度统计"""
    # 去除块注释 /* */（C 系）
    content = re.sub(r"/\*.*?\*/", "", content, flags=re.DOTALL)
    # 去除行注释 // 和 #（避免破坏字符串）
    lines = []
    for line in content.split("\n"):
        # 简单处理：去掉行尾注释
        stripped = re.sub(r"(//|#).*$", "", line)
        lines.append(stripped)
    return "\n".join(lines)


def analyze_function(func_name, body_lines):
    """计算单个函数的复杂度"""
    complexity = 1  # 基础复杂度
    for line in body_lines:
        for pattern in COMPILED_KEYWORDS:
            if pattern.search(line):
                complexity += 1
    return complexity


def extract_functions(filepath):
    """从文件中提取所有函数及其代码"""
    content = Path(filepath).read_text(encoding="utf-8", errors="ignore")
    content = strip_comments(content)
    lines = content.split("\n")
    total_lines = len(lines)

    functions = []
    current_func = None
    current_body = []
    brace_balance = 0

    for i, line in enumerate(lines, 1):
        # 检测函数定义
        matched = None
        for pat in FUNC_PATTERNS:
            m = pat.match(line)
            if m:
                matched = m
                break

        if matched:
            # 保存上一个函数
            if current_func:
                functions.append((current_func, current_body))
            current_func = matched.group(1)
            current_body = [line]

            # 统计本行的括号平衡（处理单行函数体）
            brace_balance = line.count("{") - line.count("}")
            # Python 函数以冒号结束，下一行缩进开始函数体
            if not line.rstrip().endswith(":"):
                continue
        elif current_func is not None:
            current_body.append(line)
            # 维护括号平衡（对 C 系语言）
            brace_balance += line.count("{") - line.count("}")

            # Python: 通过缩进判断函数结束
            stripped = line.strip()
            if stripped and not line.startswith((" ", "\t")):
                # 非缩进行 -> Python 函数结束
                if not line.rstrip().endswith(":"):
                    functions.append((current_func, current_body))
                    current_func = None
                    current_body = []
            # C 系：括号归零表示函数结束
            elif brace_balance <= 0 and "{" in current_body[0] and brace_balance == 0 and current_func:
                functions.append((current_func, current_body))
                current_func = None
                current_body = []

    if current_func:
        functions.append((current_func, current_body))

    return lines, functions


def analyze_file(filepath):
    """分析单个文件"""
    try:
        lines, functions = extract_functions(filepath)
    except Exception as e:
        return {"file": filepath, "error": str(e)}

    results = []
    for name, body in functions:
        # 过滤过短的"函数"（可能误判）
        if len([l for l in body if l.strip()]) < 2:
            continue
        complexity = analyze_function(name, body)
        results.append({
            "name": name,
            "line_count": len(body),
            "complexity": complexity,
            "start_line": None  # 可通过行号进一步优化
        })

    # 排序：复杂度从高到低
    results.sort(key=lambda x: x["complexity"], reverse=True)

    return {
        "file": filepath,
        "total_lines": len(lines),
        "function_count": len(results),
        "functions": results
    }


def scan_dir(dirpath):
    """扫描整个目录"""
    all_files = []
    for root, dirs, files in os.walk(dirpath):
        dirs[:] = [d for d in dirs if d not in IGNORE_DIRS]
        for f in files:
            if Path(f).suffix in EXTENSIONS:
                all_files.append(os.path.join(root, f))
    return all_files


def print_report(file_results, threshold):
    """输出分析报告"""
    print(f"{'函数':<35} {'复杂度':>6} {'行数':>6}  状态")
    print("-" * 60)

    has_high = False
    for fr in file_results:
        if "error" in fr:
            print(f"  [ERR] {fr['file']}: {fr['error']}")
            continue
        for func in fr["functions"]:
            name = func["name"][:35]
            cc = func["complexity"]
            lines = func["line_count"]
            status = "⚠️ 过高" if cc > threshold else ""
            if cc > threshold:
                has_high = True
            print(f"{name:<35} {cc:>6} {lines:>6}  {status}")

    print(f"\n统计: {sum(fr.get('function_count', 0) for fr in file_results)} 个函数"
          f" | 平均复杂度: {sum(f['complexity'] for fr in file_results for f in fr.get('functions', [])) / max(1, sum(fr.get('function_count', 0) for fr in file_results)):.1f}")
    print(f"阈值: {threshold} (超过视为复杂)")
    return has_high


def main():
    parser = argparse.ArgumentParser(description="DevFlow 代码复杂度分析器")
    parser.add_argument("--file", help="要分析的文件")
    parser.add_argument("--dir", default=".", help="要分析的目录")
    parser.add_argument("--threshold", type=int, default=10,
                        help="复杂度阈值（默认 10）")
    parser.add_argument("--format", choices=["text", "json"], default="text")
    args = parser.parse_args()

    if args.file:
        file_results = [analyze_file(args.file)]
    else:
        files = scan_dir(args.dir)
        file_results = [analyze_file(f) for f in files]

    if args.format == "json":
        print(json.dumps(file_results, ensure_ascii=False, indent=2))
        return

    has_high = print_report(file_results, args.threshold)
    if has_high:
        exit(1)


if __name__ == "__main__":
    main()
