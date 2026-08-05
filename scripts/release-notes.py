#!/usr/bin/env python3
"""
DevFlow - 发布说明生成
从 git log 自动生成 CHANGELOG / 发布说明，按 Conventional Commits 分类
Usage: python release-notes.py --dir .
       python release-notes.py --dir . --since v1.0.0
       python release-notes.py --dir . --output CHANGELOG.md
"""

import argparse
import json
import subprocess
import sys
from datetime import datetime
from pathlib import Path

# Conventional Commits 类型 → 中文标题
TYPE_TITLES = {
    "feat": "🚀 新功能",
    "fix": "🐛 修复",
    "docs": "📚 文档",
    "style": "🎨 样式",
    "refactor": "♻️ 重构",
    "perf": "⚡ 性能",
    "test": "🧪 测试",
    "build": "📦 构建",
    "ci": "🤖 CI/CD",
    "chore": "🔧 杂项",
    "revert": "↩️ 回滚",
    "other": "📝 其他",
}


def run_git(cmd, cwd="."):
    """运行 git 命令"""
    try:
        r = subprocess.run(["git"] + cmd, cwd=cwd, capture_output=True, text=True,
                           encoding="utf-8", errors="replace", timeout=30)
        return r.stdout.strip()
    except Exception:
        return ""


def parse_commit(line):
    """解析单行 git log 输出"""
    # 格式: hash|author|date|subject
    parts = line.split("|", 3)
    if len(parts) < 4:
        return None
    hash_, author, date, subject = parts[0], parts[1], parts[2], parts[3]

    # 提取 Conventional Commit 类型
    commit_type = "other"
    desc = subject
    scope = ""
    if ":" in subject:
        prefix, _, desc = subject.partition(":")
        prefix = prefix.strip().lower()
        desc = desc.strip()
        if "(" in prefix and ")" in prefix:
            commit_type, _, scope = prefix.partition("(")
            scope = scope.rstrip(")")
        elif prefix in TYPE_TITLES:
            commit_type = prefix

    return {
        "hash": hash_[:8],
        "author": author,
        "date": date[:10],
        "subject": subject,
        "type": commit_type if commit_type in TYPE_TITLES else "other",
        "scope": scope,
        "description": desc,
    }


def get_commits(cwd=".", since=None):
    """获取提交列表"""
    args = ["log", "--format=%h|%an|%ci|%s"]
    if since:
        args.append(f"{since}..HEAD")
    output = run_git(args, cwd)
    if not output:
        return []
    return [c for c in (parse_commit(line) for line in output.split("\n")) if c]


def generate_markdown(commits, project_name, since=None):
    """生成 Markdown 发布说明"""
    if not commits:
        return f"# {project_name} 发布说明\n\n暂无提交记录。"

    # 按类型分组
    grouped = {}
    for c in commits:
        grouped.setdefault(c["type"], []).append(c)

    now = datetime.now().strftime("%Y-%m-%d")
    lines = [f"# {project_name} 更新日志", "", f"> 生成时间：{now}", ""]
    if since:
        lines.append(f"> 范围：`{since}` .. HEAD")
        lines.append("")

    lines.append(f"本次共 {len(commits)} 个提交：")
    lines.append("")

    for commit_type in TYPE_TITLES:
        if commit_type not in grouped:
            continue
        lines.append(f"## {TYPE_TITLES[commit_type]}")
        lines.append("")
        for c in grouped[commit_type]:
            scope = f"**{c['scope']}** " if c["scope"] else ""
            lines.append(f"- {scope}{c['description']} ({c['hash']}, {c['author']})")
        lines.append("")

    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser(description="DevFlow 发布说明生成")
    parser.add_argument("--dir", default=".", help="Git 仓库目录")
    parser.add_argument("--since", help="起始标签或 commit")
    parser.add_argument("--output", help="输出文件")
    parser.add_argument("--json", action="store_true", help="JSON 输出")
    args = parser.parse_args()

    cwd = args.dir
    if not run_git(["rev-parse", "--is-inside-work-tree"], cwd) == "true":
        print("错误: 不是 Git 仓库", file=sys.stderr)
        sys.exit(1)

    commits = get_commits(cwd, args.since)

    if args.json:
        print(json.dumps({"count": len(commits), "commits": commits},
                         ensure_ascii=False, indent=2))
        return

    project_name = Path(cwd).name or "项目"
    markdown = generate_markdown(commits, project_name, args.since)

    if args.output:
        Path(args.output).write_text(markdown, encoding="utf-8")
        print(f"发布说明已保存: {args.output}")
    else:
        print(markdown)


if __name__ == "__main__":
    main()
