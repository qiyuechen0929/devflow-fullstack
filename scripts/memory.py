#!/usr/bin/env python3
"""
DevFlow - 项目记忆管理
跨会话保存项目关键决策、经验教训、待办事项，让 AI 在后续会话中记住项目上下文。

存储位置：.devflow/memory.md

Usage:
  python memory.py add "关键决策：使用 TypeScript 重构"
  python memory.py list
  python memory.py search 数据库
  python memory.py delete <index>
  python memory.py clear
"""

import argparse
import json
import os
import sys
from datetime import datetime
from pathlib import Path


def get_memory_file(project_dir):
    """获取记忆文件路径"""
    return Path(project_dir) / ".devflow" / "memory.md"


def load_memories(project_dir):
    """加载记忆列表"""
    mf = get_memory_file(project_dir)
    if not mf.exists():
        return []
    entries = []
    current = None
    for line in mf.read_text(encoding="utf-8", errors="ignore").split("\n"):
        if line.startswith("## ["):
            if current:
                entries.append(current)
            # 解析 "## [时间] 标题"
            try:
                header = line[3:].strip()
                time_part, _, title = header.partition("] ")
                current = {"time": time_part.lstrip("["), "title": title, "body": []}
            except Exception:
                current = {"time": "", "title": line, "body": []}
        elif current and line.strip() and not line.startswith("---"):
            current["body"].append(line.strip())
    if current:
        entries.append(current)
    return entries


def add_memory(project_dir, content, tag=""):
    """添加一条记忆"""
    mf = get_memory_file(project_dir)
    mf.parent.mkdir(parents=True, exist_ok=True)

    now = datetime.now().strftime("%Y-%m-%d %H:%M")
    entry = f"## [{now}] {content}\n"
    if tag:
        entry += f"- 标签: `{tag}`\n"
    entry += "---\n"

    if mf.exists():
        with open(mf, "a", encoding="utf-8") as f:
            f.write("\n" + entry)
    else:
        mf.write_text(f"# DevFlow 项目记忆\n\n{entry}", encoding="utf-8")

    return entry


def list_memories(project_dir, search=None):
    """列出记忆"""
    entries = load_memories(project_dir)
    if search:
        entries = [e for e in entries
                   if search.lower() in (e["title"] + " ".join(e["body"])).lower()]

    if not entries:
        print("暂无记忆。用 `python memory.py add \"内容\"` 添加。")
        return

    for i, e in enumerate(entries):
        print(f"[{i}] ({e['time']}) {e['title']}")
        for b in e["body"]:
            print(f"    {b}")


def delete_memory(project_dir, index):
    """删除一条记忆"""
    entries = load_memories(project_dir)
    if index < 0 or index >= len(entries):
        print(f"错误: 索引 {index} 超出范围 (0-{len(entries)-1})")
        return False

    entries.pop(index)
    mf = get_memory_file(project_dir)
    if entries:
        lines = ["# DevFlow 项目记忆\n"]
        for e in entries:
            lines.append(f"## [{e['time']}] {e['title']}")
            for b in e["body"]:
                lines.append(f"- {b}" if not b.startswith("- ") else b)
            lines.append("---")
            lines.append("")
        mf.write_text("\n".join(lines), encoding="utf-8")
    else:
        mf.write_text("# DevFlow 项目记忆\n", encoding="utf-8")

    print(f"已删除记忆 [{index}]")
    return True


def main():
    parser = argparse.ArgumentParser(description="DevFlow 项目记忆管理")
    parser.add_argument("command", choices=["add", "list", "search", "delete", "clear"],
                        help="记忆命令")
    parser.add_argument("content", nargs="*", help="记忆内容 / 搜索词 / 索引")
    parser.add_argument("--dir", default=".", help="项目目录")
    parser.add_argument("--tag", default="", help="记忆标签")
    args = parser.parse_args()

    project_dir = os.path.abspath(args.dir)
    content = " ".join(args.content)

    if args.command == "add":
        if not content:
            print("错误: 请输入记忆内容")
            sys.exit(1)
        entry = add_memory(project_dir, content, args.tag)
        print(f"✅ 已保存记忆:\n{entry}")

    elif args.command == "list":
        list_memories(project_dir)

    elif args.command == "search":
        if not content:
            print("错误: 请输入搜索词")
            sys.exit(1)
        list_memories(project_dir, content)

    elif args.command == "delete":
        if not content.isdigit():
            print("错误: 请输入要删除的索引（用 list 查看）")
            sys.exit(1)
        delete_memory(project_dir, int(content))

    elif args.command == "clear":
        mf = get_memory_file(project_dir)
        if mf.exists():
            mf.write_text("# DevFlow 项目记忆\n", encoding="utf-8")
            print("已清空所有记忆")
        else:
            print("无记忆文件")


if __name__ == "__main__":
    main()
