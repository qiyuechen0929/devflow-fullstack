#!/usr/bin/env python3
"""
DevFlow - Git Helper
Usage:
  python git-helper.py --mode commit   # generate conventional commit from staged diff
  python git-helper.py --mode pr       # generate PR description
  python git-helper.py --mode changelog --dir .
"""

import argparse, subprocess, sys, os, json
from datetime import datetime

def run_git(cmd, cwd="."):
    try:
        r = subprocess.run(["git"] + cmd, cwd=cwd, capture_output=True, text=True)
        return r.stdout.strip()
    except Exception:
        return ""

def get_diff(cwd=".", staged=True):
    cmd = ["diff", "--cached"] if staged else ["diff"]
    return run_git(cmd, cwd)

def get_branch(cwd="."):
    return run_git(["rev-parse", "--abbrev-ref", "HEAD"], cwd)

def get_log(since="1 week ago", cwd="."):
    return run_git(["log", f"--since={since}", "--oneline", "--no-merges"], cwd)

def classify_commit(diff_text):
    """Classify commit type based on diff content"""
    if not diff_text:
        return "chore", "杂项更新"

    if any(kw in diff_text.lower() for kw in ["fix", "bug", "error", "crash", "修复"]):
        return "fix", "修复"
    if any(kw in diff_text.lower() for kw in ["feat", "add", "new", "新增", "添加"]):
        return "feat", "新功能"
    if any(kw in diff_text.lower() for kw in ["refactor", "重构", "clean", "simplify"]):
        return "refactor", "重构"
    if any(kw in diff_text.lower() for kw in ["doc", "readme", "文档"]):
        return "docs", "文档"
    if any(kw in diff_text.lower() for kw in ["test", "spec", "测试"]):
        return "test", "测试"
    if any(kw in diff_text.lower() for kw in ["style", "format", "格式"]):
        return "style", "格式"
    if any(kw in diff_text.lower() for kw in ["ci", "pipeline", "docker", "deploy"]):
        return "ci", "CI/CD"
    return "chore", "杂项"

def generate_commit(cwd="."):
    diff = get_diff(cwd)
    if not diff:
        print("无暂存变更。先用 git add 暂存文件。")
        return

    commit_type, type_cn = classify_commit(diff)

    # Extract changed files
    files = run_git(["diff", "--cached", "--name-only"], cwd).split("\n")
    file_list = ", ".join(files[:3])
    if len(files) > 3:
        file_list += f" 等{len(files)}个文件"

    # Generate commit message
    msg = f"{commit_type}: {type_cn} {file_list}"
    if len(msg) > 72:
        msg = f"{commit_type}: {type_cn} ({len(files)}个文件变更)"

    print(f"\n建议 commit:")
    print(f"  {msg}")
    print(f"\n变更文件: {len(files)}个")
    for f in files[:10]:
        print(f"  - {f}")

def generate_pr_description(cwd="."):
    branch = get_branch(cwd)
    diff = get_diff(cwd, staged=False)
    log = get_log("1 week ago", cwd)

    changes = diff.split("\n")
    added = len([l for l in changes if l.startswith("+") and not l.startswith("+++")])
    removed = len([l for l in changes if l.startswith("-") and not l.startswith("---")])

    print(f"""## 概述

- **分支**: {branch}
- **变更**: +{added}/-{removed} 行

## 改动内容

TODO: 简述主要改动

## 测试

- [ ] 单元测试通过
- [ ] 手工验证通过

## 截图 (如有 UI 变更)

TODO
""")

def generate_changelog(dirpath="."):
    log = get_log("2 weeks ago", dirpath)
    if not log:
        print("无提交记录")
        return

    entries = log.split("\n")
    grouped = {}
    for e in entries:
        if " " in e:
            _, msg = e.split(" ", 1)
            prefix = msg.split(":")[0] if ":" in msg else "other"
            grouped.setdefault(prefix, []).append(msg)

    print(f"# Changelog ({datetime.now().strftime('%Y-%m-%d')})\n")
    for category, msgs in sorted(grouped.items()):
        emoji_map = {"feat":"✨","fix":"🐛","refactor":"♻️","docs":"📝","test":"[OK]","style":"💄","ci":"🔧"}
        emoji = emoji_map.get(category, "🔹")
        print(f"## {emoji} {category}")
        for m in msgs[:5]:
            print(f"- {m}")
        print()

def main():
    parser = argparse.ArgumentParser(description="DevFlow Git Helper")
    parser.add_argument("--mode", choices=["commit","pr","changelog"], default="commit")
    parser.add_argument("--dir", default=".", help="仓库路径")
    args = parser.parse_args()

    if not os.path.isdir(os.path.join(args.dir, ".git")):
        print(f"错误: {args.dir} 不是 Git 仓库")
        sys.exit(1)

    if args.mode == "commit":
        generate_commit(args.dir)
    elif args.mode == "pr":
        generate_pr_description(args.dir)
    elif args.mode == "changelog":
        generate_changelog(args.dir)

if __name__ == "__main__":
    main()
