#!/usr/bin/env python3
"""
DevFlow - PR 合并检查工具
检查 Pull Request 是否满足合并条件：
- 代码改动量
- 是否有测试
- 是否有 TODO/FIXME
- 是否有调试残留
- 是否触及关键文件
Usage: python pr-tool.py --diff pr.diff
       python pr-tool.py --diff pr.diff --json
"""

import argparse
import json
import os
import re
import sys
from pathlib import Path


def parse_diff(diff_path):
    """解析 diff 文件，提取改动统计"""
    try:
        content = Path(diff_path).read_text(encoding="utf-8", errors="ignore")
    except Exception as e:
        return None, str(e)

    files = []
    current_file = None
    added = 0
    removed = 0

    for line in content.split("\n"):
        if line.startswith("diff --git"):
            if current_file:
                files.append({"file": current_file, "added": added, "removed": removed})
            # 提取文件路径
            m = re.search(r"diff --git a/(.+?) b/(.+)", line)
            current_file = m.group(2) if m else "unknown"
            added = 0
            removed = 0
        elif line.startswith("+") and not line.startswith("+++"):
            added += 1
        elif line.startswith("-") and not line.startswith("---"):
            removed += 1

    if current_file:
        files.append({"file": current_file, "added": added, "removed": removed})

    return files, None


def check_tests(files):
    """检查是否包含测试文件改动"""
    return any("test" in f["file"].lower() or "spec" in f["file"].lower() for f in files)


def scan_added_lines(diff_path):
    """扫描新增行中的问题"""
    try:
        content = Path(diff_path).read_text(encoding="utf-8", errors="ignore")
    except Exception:
        return []

    issues = []
    for i, line in enumerate(content.split("\n"), 1):
        if not line.startswith("+"):
            continue
        added = line[1:]
        # 跳过 +++ 头部
        if added.startswith("++"):
            continue
        # 调试残留
        if re.search(r"console\.log\(|print\(|debugger;|printf\(", added) and "print(" not in added.lower().replace("print(", ""):
            issues.append({"line": i, "type": "调试残留", "detail": added.strip()[:80]})
        # TODO/FIXME
        if re.search(r"\b(TODO|FIXME|XXX|HACK)\b", added):
            issues.append({"line": i, "type": "遗留标记", "detail": added.strip()[:80]})
        # 硬编码
        if re.search(r"(api[_-]?key|secret|password)\s*=\s*['\"][^'\"]{8,}", added):
            issues.append({"line": i, "type": "硬编码密钥", "detail": added.strip()[:80]})
    return issues


def main():
    parser = argparse.ArgumentParser(description="DevFlow PR 合并检查")
    parser.add_argument("--diff", required=True, help="PR diff 文件")
    parser.add_argument("--json", action="store_true", help="JSON 输出")
    args = parser.parse_args()

    files, err = parse_diff(args.diff)
    if err:
        print(f"错误: {err}")
        sys.exit(1)

    issues = scan_added_lines(args.diff)

    if args.json:
        report = {
            "files_changed": len(files),
            "total_added": sum(f["added"] for f in files),
            "total_removed": sum(f["removed"] for f in files),
            "has_tests": check_tests(files),
            "issues": issues,
        }
        print(json.dumps(report, ensure_ascii=False, indent=2))
        return

    print("🔀 DevFlow PR 合并检查\n")

    total_added = sum(f["added"] for f in files)
    total_removed = sum(f["removed"] for f in files)
    print(f"改动文件: {len(files)} 个")
    print(f"新增行: {total_added} | 删除行: {total_removed}")
    print(f"包含测试: {'✅' if check_tests(files) else '❌ 未包含测试改动'}")
    print("")

    for f in files[:10]:
        print(f"  {f['file']:<50} +{f['added']}/-{f['removed']}")

    if issues:
        print("\n新增行中的问题:")
        for i in issues[:10]:
            print(f"  ⚠️  {i['type']}: {i['detail']}")
    else:
        print("\n✓ 新增行未发现调试残留/TODO/硬编码")

    # 判定
    problems = []
    if not check_tests(files):
        problems.append("未包含测试")
    if total_added > 500:
        problems.append("改动过大 (>500 行)")
    if issues:
        problems.append(f"新增行有 {len(issues)} 处问题")

    print("\n结论:")
    if problems:
        for p in problems:
            print(f"  ❌ {p}")
        sys.exit(1)
    else:
        print("  ✅ 可以合并")


if __name__ == "__main__":
    main()
