#!/usr/bin/env python3
"""
DevFlow - Git 提交统计分析
统计提交数量、活跃度、贡献者、提交类型分布
Usage: python git-stats.py --dir .
       python git-stats.py --dir . --since 2026-01-01
       python git-stats.py --dir . --top 5
"""

import argparse
import json
import subprocess
import sys
from pathlib import Path
from collections import Counter
from datetime import datetime


def run_git(cmd, cwd="."):
    """运行 git 命令"""
    try:
        result = subprocess.run(
            ["git"] + cmd,
            cwd=cwd,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=30
        )
        return result.stdout.strip()
    except (subprocess.TimeoutExpired, FileNotFoundError):
        return ""
    except Exception:
        return ""


def is_git_repo(cwd="."):
    """检查是否是 git 仓库"""
    return run_git(["rev-parse", "--is-inside-work-tree"], cwd) == "true"


def get_commit_count(since=None, cwd="."):
    """获取提交数量"""
    args = ["rev-list", "--count", "HEAD"]
    if since:
        args.append(f"--since={since}")
    return run_git(args, cwd) or "0"


def get_contributors(cwd="."):
    """获取贡献者统计"""
    log = run_git(
        ["shortlog", "-sne", "HEAD"],
        cwd
    )
    contributors = []
    for line in log.split("\n"):
        if not line.strip():
            continue
        parts = line.strip().split("\t")
        if len(parts) == 2:
            count = parts[0].strip()
            identity = parts[1].strip()
            # 解析 "Name <email>"
            if "<" in identity:
                name, email = identity.rsplit("<", 1)
                contributors.append({
                    "name": name.strip(),
                    "email": email.rstrip(">"),
                    "commits": int(count)
                })
    return contributors


def get_commit_types(cwd="."):
    """统计提交类型分布（基于 conventional commits 前缀）"""
    log = run_git(["log", "--format=%s", "HEAD"], cwd)
    types = Counter()
    for subject in log.split("\n"):
        subject = subject.strip()
        if ":" in subject:
            prefix = subject.split(":", 1)[0].strip().lower()
            # 去除 scope: type(scope) 的括号
            if "(" in prefix:
                prefix = prefix.split("(")[0]
            if prefix in ("feat", "fix", "docs", "style", "refactor", "perf",
                          "test", "build", "ci", "chore", "revert"):
                types[prefix] += 1
            else:
                types["other"] += 1
        else:
            types["other"] += 1
    return dict(types)


def get_activity(cwd="."):
    """获取最近活跃信息"""
    last_commit = run_git(["log", "-1", "--format=%ci", "HEAD"], cwd)
    current = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    return {
        "last_commit": last_commit,
        "now": current
    }


def get_top_changed_files(cwd=".", top=10):
    """获取改动最多的文件"""
    log = run_git(["log", "--name-only", "--format=", "HEAD"], cwd)
    files = [f.strip() for f in log.split("\n") if f.strip()]
    return Counter(files).most_common(top)


def main():
    parser = argparse.ArgumentParser(description="DevFlow Git 提交统计分析")
    parser.add_argument("--dir", default=".", help="Git 仓库目录")
    parser.add_argument("--since", help="统计起始日期 (YYYY-MM-DD)")
    parser.add_argument("--top", type=int, default=10, help="显示前 N 个文件")
    parser.add_argument("--format", choices=["text", "json"], default="text")
    args = parser.parse_args()

    if not is_git_repo(args.dir):
        print(f"错误: {args.dir} 不是 Git 仓库", file=sys.stderr)
        sys.exit(1)

    if args.format == "json":
        report = {
            "commit_count": int(get_commit_count(args.since, args.dir)),
            "contributors": get_contributors(args.dir),
            "commit_types": get_commit_types(args.dir),
            "activity": get_activity(args.dir),
            "top_files": [{"file": f, "changes": c}
                          for f, c in get_top_changed_files(args.dir, args.top)]
        }
        print(json.dumps(report, ensure_ascii=False, indent=2))
        return

    print("=== DevFlow Git 统计 ===")
    print(f"\n提交总数: {get_commit_count(args.since, args.dir)} 次")

    print("\n贡献者:")
    for c in get_contributors(args.dir)[:10]:
        print(f"  {c['name']:<20} {c['commits']:>4} 次提交")

    print("\n提交类型分布:")
    for t, count in get_commit_types(args.dir).items():
        bar = "█" * min(count, 40)
        print(f"  {t:<10} {count:>4}  {bar}")

    activity = get_activity(args.dir)
    print(f"\n最近提交: {activity['last_commit']}")

    print(f"\n改动最多的文件 (Top {args.top}):")
    for i, (file, count) in enumerate(get_top_changed_files(args.dir, args.top), 1):
        print(f"  {i:>2}. {file:<50} {count} 次")


if __name__ == "__main__":
    main()
