#!/usr/bin/env python3
"""
DevFlow - TDD 检查
检查项目是否符合测试驱动开发（Test-Driven Development）实践：
- 测试覆盖率估算
- 测试与源码比例
- 命名规范 (test_*.py)
- 关键模块是否有对应测试
Usage: python tdd-check.py --dir .
       python tdd-check.py --dir . --json
"""

import argparse
import json
import os
import sys
from pathlib import Path

IGNORE_DIRS = {"node_modules", ".git", "__pycache__", "dist", "build", ".next",
               "target", "vendor", ".venv", "venv"}


def find_files(project_dir, exts, ignore_dirs=IGNORE_DIRS):
    """查找指定扩展名的文件"""
    results = []
    for root, dirs, files in os.walk(project_dir):
        dirs[:] = [d for d in dirs if d not in ignore_dirs]
        for f in files:
            if f.endswith(exts):
                results.append(os.path.join(root, f))
    return results


def main():
    parser = argparse.ArgumentParser(description="DevFlow TDD 检查")
    parser.add_argument("--dir", default=".", help="项目目录")
    parser.add_argument("--json", action="store_true", help="JSON 输出")
    args = parser.parse_args()

    project_dir = os.path.abspath(args.dir)

    # 源码文件（排除测试和脚本自身的扫描逻辑）
    source_files = [f for f in find_files(project_dir, (".py", ".js", ".ts", ".jsx", ".tsx", ".java", ".go"))
                    if "test" not in Path(f).name.lower() and "spec" not in Path(f).name.lower()
                    and "__pycache__" not in f and ".claude" not in f and "scripts/" not in f and "devflow" not in Path(f).name.lower()]
    test_files = [f for f in find_files(project_dir, (".py", ".js", ".ts", ".jsx", ".tsx", ".java", ".go"))
                  if ("test" in Path(f).name.lower() or "spec" in Path(f).name.lower())]

    report = {
        "source_files": len(source_files),
        "test_files": len(test_files),
        "test_ratio": round(len(test_files) / max(1, len(source_files)), 2),
    }

    # 检查测试命名规范
    bad_named = [f for f in test_files if not (Path(f).name.startswith("test_")
                                               or Path(f).name.startswith("test")
                                               or Path(f).name.endswith("_test.go")
                                               or Path(f).name.endswith(".spec."))]
    report["bad_named_tests"] = [Path(f).name for f in bad_named]

    # 找没有测试的关键模块（取源码文件的前 5 个）
    test_names = {Path(f).stem.replace("test_", "").replace("Test", "").lower() for f in test_files}
    untested = []
    for sf in source_files[:50]:
        stem = Path(sf).stem.lower()
        if not any(stem in tn or tn in stem for tn in test_names):
            untested.append(Path(sf).name)
    report["untested_modules"] = untested[:8]

    if args.json:
        print(json.dumps(report, ensure_ascii=False, indent=2))
        return

    print("🧪 DevFlow TDD 检查\n")
    print(f"源码文件: {report['source_files']} 个")
    print(f"测试文件: {report['test_files']} 个")
    print(f"测试/源码比: {report['test_ratio']} (建议 ≥0.5)")
    print("")

    if report["bad_named_tests"]:
        print("⚠️ 命名不规范:")
        for n in report["bad_named_tests"]:
            print(f"  - {n}")
    else:
        print("✅ 测试命名规范")

    if report["untested_modules"]:
        print("\n⚠️ 可能缺少测试的模块:")
        for m in report["untested_modules"]:
            print(f"  - {m}")
    else:
        print("\n✅ 主要模块都有对应测试")

    print("\n结论:")
    if report["test_ratio"] >= 0.5 and not report["untested_modules"]:
        print("  ✅ TDD 实践良好")
    elif report["test_ratio"] >= 0.2:
        print("  ⚠️ 有一定测试基础，建议补充")
        sys.exit(1)
    else:
        print("  ❌ 测试严重不足，建议引入 TDD")
        sys.exit(1)


if __name__ == "__main__":
    main()
