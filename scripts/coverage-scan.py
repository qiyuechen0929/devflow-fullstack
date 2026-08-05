#!/usr/bin/env python3
"""
DevFlow - 测试覆盖率估算
无需安装 coverage 工具，通过静态分析估算测试覆盖率：
- 检测源码模块是否被测试文件 import
- 检测源码函数是否在测试中出现
- 计算未测试的函数/模块列表
Usage: python coverage-scan.py --dir .
       python coverage-scan.py --dir . --json
"""

import argparse
import json
import os
import re
import sys
from pathlib import Path

IGNORE_DIRS = {"node_modules", ".git", "__pycache__", "dist", "build", ".next",
               "target", "vendor", ".venv", "venv"}


def is_test_file(name):
    """判断是否是测试文件"""
    lower = name.lower()
    return lower.startswith("test_") or lower.startswith("test.") or \
           lower.endswith("_test.py") or lower.endswith(".spec.") or \
           "test" in lower and "test_" in lower or "_test" in lower


def collect_python_files(project_dir):
    """收集 Python 文件"""
    src_files = []
    test_files = []
    for root, dirs, files in os.walk(project_dir):
        dirs[:] = [d for d in dirs if d not in IGNORE_DIRS]
        for f in files:
            if f.endswith(".py"):
                fp = os.path.join(root, f)
                rel = os.path.relpath(fp, project_dir)
                if "scripts" in rel or "devflow" in rel or "workflow" in rel or "agents" in rel:
                    continue
                if is_test_file(f):
                    test_files.append(fp)
                else:
                    src_files.append(fp)
    return src_files, test_files


def extract_imports(filepath):
    """提取文件的 import 语句"""
    try:
        content = Path(filepath).read_text(encoding="utf-8", errors="ignore")
    except Exception:
        return set()

    imports = set()
    for m in re.finditer(r"(?:from\s+([\w.]+)\s+import|\bimport\s+([\w.]+))", content):
        module = m.group(1) or m.group(2)
        imports.add(module.split(".")[0])
    return imports


def extract_functions(filepath):
    """提取文件定义的函数名"""
    try:
        content = Path(filepath).read_text(encoding="utf-8", errors="ignore")
    except Exception:
        return set()

    funcs = set()
    for m in re.finditer(r"^\s*(?:async\s+def|def)\s+(\w+)\s*\(", content, re.MULTILINE):
        if not m.group(1).startswith("_"):
            funcs.add(m.group(1))
    return funcs


def main():
    parser = argparse.ArgumentParser(description="DevFlow 测试覆盖率估算")
    parser.add_argument("--dir", default=".", help="项目目录")
    parser.add_argument("--json", action="store_true", help="JSON 输出")
    args = parser.parse_args()

    project_dir = os.path.abspath(args.dir)
    src_files, test_files = collect_python_files(project_dir)

    # 收集测试中引用的模块名和函数名
    tested_modules = set()
    tested_functions = set()
    for tf in test_files:
        tested_modules.update(extract_imports(tf))
        try:
            content = Path(tf).read_text(encoding="utf-8", errors="ignore")
            tested_functions.update(re.findall(r"\b(\w+)\s*\(", content))
        except Exception:
            pass

    # 分析每个源码模块
    module_coverage = []
    total_functions = 0
    covered_functions = 0

    for sf in src_files:
        name = Path(sf).stem
        funcs = extract_functions(sf)
        # 模块被测试引用 = 已覆盖
        module_tested = name in tested_modules
        # 函数级覆盖估算
        covered_funcs = [f for f in funcs if f in tested_functions]
        total_functions += len(funcs)
        covered_functions += len(covered_funcs)

        module_coverage.append({
            "module": os.path.relpath(sf, project_dir),
            "functions": len(funcs),
            "covered_functions": len(covered_funcs),
            "module_tested": module_tested,
        })

    if total_functions == 0:
        function_cov = 0
    else:
        function_cov = round(covered_functions / total_functions * 100)

    report = {
        "source_modules": len(src_files),
        "test_files": len(test_files),
        "tested_modules": sum(1 for m in module_coverage if m["module_tested"]),
        "total_functions": total_functions,
        "covered_functions": covered_functions,
        "estimated_coverage": function_cov,
        "untested_modules": [m["module"] for m in module_coverage if not m["module_tested"]][:10],
        "module_details": module_coverage[:20],
    }

    if args.json:
        print(json.dumps(report, ensure_ascii=False, indent=2))
        return

    print("📊 DevFlow 测试覆盖率估算\n")
    print(f"源码模块: {report['source_modules']} | 测试文件: {report['test_files']}")
    print(f"被测试引用的模块: {report['tested_modules']}/{report['source_modules']}")
    print(f"函数覆盖估算: {report['covered_functions']}/{report['total_functions']} "
          f"({report['estimated_coverage']}%)")
    print("")

    if report["untested_modules"]:
        print("⚠️ 未测试的模块:")
        for m in report["untested_modules"]:
            print(f"  - {m}")

    print(f"\n估算覆盖率: {report['estimated_coverage']}%")
    if report["estimated_coverage"] >= 60:
        print("结论: ✅ 覆盖率良好")
    elif report["estimated_coverage"] >= 30:
        print("结论: ⚠️ 覆盖率一般，建议补充测试")
        sys.exit(1)
    else:
        print("结论: ❌ 覆盖率偏低，建议补充测试")
        sys.exit(1)


if __name__ == "__main__":
    main()
