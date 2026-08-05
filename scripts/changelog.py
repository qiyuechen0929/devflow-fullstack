#!/usr/bin/env python3
"""
DevFlow - Changelog Generator
从 Git 历史自动生成变更日志
Usage:
  python changelog.py --dir .
  python changelog.py --dir . --from v1.0.0 --to v1.1.0
  python changelog.py --dir . --format markdown
  python changelog.py --dir . --output CHANGELOG.md
"""

import argparse
import json
import re
import subprocess
import sys
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Tuple

# Conventional Commits 类型映射
COMMIT_TYPES = {
    "feat": {"title": "Features", "emoji": "[feat]"},
    "fix": {"title": "Bug Fixes", "emoji": "[fix]"},
    "docs": {"title": "Documentation", "emoji": "[docs]"},
    "style": {"title": "Styles", "emoji": "[style]"},
    "refactor": {"title": "Refactoring", "emoji": "[refactor]"},
    "perf": {"title": "Performance", "emoji": "[perf]"},
    "test": {"title": "Tests", "emoji": "[test]"},
    "build": {"title": "Build", "emoji": "[build]"},
    "ci": {"title": "CI/CD", "emoji": "[ci]"},
    "chore": {"title": "Chores", "emoji": "[chore]"},
    "revert": {"title": "Reverts", "emoji": "[revert]"},
}


def run_git_command(args: List[str], cwd: str = ".") -> Tuple[str, int]:
    """运行 Git 命令"""
    try:
        result = subprocess.run(
            ["git"] + args,
            cwd=cwd,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace"
        )
        return result.stdout.strip(), result.returncode
    except Exception as e:
        return str(e), -1


def get_tags(cwd: str = ".") -> List[Dict]:
    """获取所有标签"""
    output, code = run_git_command(["tag", "--sort=-v:refdate"], cwd)
    if code != 0:
        return []

    tags = []
    for tag in output.split("\n"):
        tag = tag.strip()
        if tag:
            # 获取标签日期
            date_output, _ = run_git_command(["log", "-1", "--format=%ai", tag], cwd)
            tags.append({
                "name": tag,
                "date": date_output[:10] if date_output else ""
            })

    return tags


def get_commits(from_ref: str = None, to_ref: str = "HEAD", cwd: str = ".") -> List[Dict]:
    """获取 Git 提交记录"""
    # 构建命令
    args = ["log", "--format=%H|%s|%an|%ai|%b", "--no-merges"]

    if from_ref and to_ref:
        args.append(f"{from_ref}..{to_ref}")
    elif to_ref:
        args.append(to_ref)

    output, code = run_git_command(args, cwd)
    if code != 0:
        return []

    commits = []
    for line in output.split("\n"):
        if not line.strip():
            continue

        parts = line.split("|", 4)
        if len(parts) >= 4:
            commit_hash = parts[0]
            subject = parts[1]
            author = parts[2]
            date = parts[3]
            body = parts[4] if len(parts) > 4 else ""

            # 解析 Conventional Commits
            commit_type, scope, description = parse_commit_message(subject)

            commits.append({
                "hash": commit_hash[:8],
                "type": commit_type,
                "scope": scope,
                "description": description or subject,
                "author": author,
                "date": date[:10],
                "body": body.strip(),
                "breaking": "BREAKING CHANGE" in body or "!" in subject
            })

    return commits


def parse_commit_message(message: str) -> Tuple[str, str, str]:
    """解析 Conventional Commits 格式"""
    # 匹配 type(scope): description
    pattern = r"^(\w+)(?:\(([^)]+)\))?\s*:\s*(.+)$"
    match = re.match(pattern, message)

    if match:
        commit_type = match.group(1).lower()
        scope = match.group(2)
        description = match.group(3)

        # 验证类型
        if commit_type in COMMIT_TYPES:
            return commit_type, scope, description

    return "other", None, message


def group_commits_by_type(commits: List[Dict]) -> Dict[str, List[Dict]]:
    """按类型分组提交"""
    groups = {}

    for commit in commits:
        commit_type = commit["type"]
        if commit_type not in groups:
            groups[commit_type] = []
        groups[commit_type].append(commit)

    return groups


def generate_markdown(commits: List[Dict], version: str = None, date: str = None) -> str:
    """生成 Markdown 格式的 CHANGELOG"""
    lines = []

    # 标题
    if version:
        lines.append(f"## {version}")
        if date:
            lines.append(f"({date})")
        lines.append("")
    else:
        lines.append("## Unreleased")
        lines.append("")

    # 按类型分组
    groups = group_commits_by_type(commits)

    # Breaking Changes
    breaking_commits = [c for c in commits if c["breaking"]]
    if breaking_commits:
        lines.append("### BREAKING CHANGES")
        lines.append("")
        for commit in breaking_commits:
            scope = f"**{commit['scope']}**: " if commit["scope"] else ""
            lines.append(f"- {scope}{commit['description']} ({commit['hash']})")
        lines.append("")

    # 按类型输出
    for commit_type in ["feat", "fix", "perf", "refactor", "docs", "style", "test", "build", "ci", "chore", "revert"]:
        if commit_type in groups:
            type_info = COMMIT_TYPES[commit_type]
            lines.append(f"### {type_info['title']}")
            lines.append("")

            for commit in groups[commit_type]:
                scope = f"**{commit['scope']}**: " if commit["scope"] else ""
                lines.append(f"- {scope}{commit['description']} ({commit['hash']})")

            lines.append("")

    # 其他类型
    if "other" in groups:
        lines.append("### Other Changes")
        lines.append("")
        for commit in groups["other"]:
            lines.append(f"- {commit['description']} ({commit['hash']})")
        lines.append("")

    # 贡献者
    authors = set(c["author"] for c in commits)
    if authors:
        lines.append("### Contributors")
        lines.append("")
        for author in sorted(authors):
            lines.append(f"- {author}")
        lines.append("")

    return "\n".join(lines)


def generate_json(commits: List[Dict], version: str = None) -> str:
    """生成 JSON 格式"""
    data = {
        "version": version or "unreleased",
        "generated_at": datetime.now().isoformat(),
        "total_commits": len(commits),
        "commits": commits,
        "summary": {}
    }

    # 统计
    groups = group_commits_by_type(commits)
    for commit_type, type_commits in groups.items():
        data["summary"][commit_type] = len(type_commits)

    return json.dumps(data, indent=2, ensure_ascii=False)


def generate_full_changelog(cwd: str = ".") -> str:
    """生成完整的 CHANGELOG（包含所有版本）"""
    tags = get_tags(cwd)

    if not tags:
        # 没有标签，只生成当前版本
        commits = get_commits(cwd=cwd)
        return generate_markdown(commits)

    lines = ["# Changelog", ""]

    # 遍历标签
    for i, tag in enumerate(tags):
        from_tag = tags[i + 1]["name"] if i + 1 < len(tags) else None
        to_tag = tag["name"]

        commits = get_commits(from_tag, to_tag, cwd)
        if commits:
            lines.append(generate_markdown(commits, to_tag, tag["date"]))

    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser(
        description="DevFlow Changelog Generator",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Generate changelog from all commits
  python changelog.py --dir .

  # Generate changelog between tags
  python changelog.py --dir . --from v1.0.0 --to v1.1.0

  # Generate full changelog with all versions
  python changelog.py --dir . --full

  # Output as JSON
  python changelog.py --dir . --format json

  # Save to file
  python changelog.py --dir . --output CHANGELOG.md
        """
    )

    parser.add_argument("--dir", "-d", default=".", help="Git repository directory")
    parser.add_argument("--from", dest="from_ref", help="From ref (tag/commit)")
    parser.add_argument("--to", dest="to_ref", default="HEAD", help="To ref (default: HEAD)")
    parser.add_argument("--version", "-v", help="Version name")
    parser.add_argument("--full", action="store_true", help="Generate full changelog")
    parser.add_argument("--format", "-f", choices=["markdown", "json"], default="markdown", help="Output format")
    parser.add_argument("--output", "-o", help="Output file path")

    args = parser.parse_args()

    # 生成完整 CHANGELOG
    if args.full:
        changelog = generate_full_changelog(args.dir)
        if args.output:
            Path(args.output).write_text(changelog, encoding="utf-8")
            print(f"Changelog saved to: {args.output}")
        else:
            print(changelog)
        return

    # 获取提交
    commits = get_commits(args.from_ref, args.to_ref, args.dir)

    if not commits:
        print("No commits found.", file=sys.stderr)
        sys.exit(0)

    # 生成 CHANGELOG
    if args.format == "json":
        changelog = generate_json(commits, args.version)
    else:
        changelog = generate_markdown(commits, args.version)

    # 输出
    if args.output:
        Path(args.output).write_text(changelog, encoding="utf-8")
        print(f"Changelog saved to: {args.output}")
    else:
        print(changelog)


if __name__ == "__main__":
    main()
