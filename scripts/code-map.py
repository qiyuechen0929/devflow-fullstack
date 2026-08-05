#!/usr/bin/env python3
"""
DevFlow - 代码地图
生成项目的代码结构地图，展示模块依赖与功能分布
Usage: python code-map.py --dir .
       python code-map.py --dir . --json
       python code-map.py --dir . --depth 2
"""

import argparse
import json
import os
import sys
from pathlib import Path

IGNORE_DIRS = {"node_modules", ".git", "__pycache__", "dist", "build", ".next",
               "target", "vendor", ".venv", "venv"}

# 目录图标
DIR_ICONS = {
    "src": "📦", "lib": "📦", "components": "🧩", "pages": "📄",
    "api": "🔌", "routes": "🔌", "services": "⚙️", "utils": "🛠️",
    "helpers": "🛠️", "models": "📊", "types": "🏷️", "interfaces": "🏷️",
    "tests": "🧪", "test": "🧪", "spec": "🧪", "docs": "📚", "doc": "📚",
    "config": "⚙️", "scripts": "📜", "public": "🌐", "assets": "🎨",
    "styles": "🎨", "css": "🎨", "hooks": "🪝", "middleware": "🔀",
    "store": "🗄️", "state": "🗄️", "db": "🗄️", "database": "🗄️",
    "deploy": "🚀", "docker": "🐳", ".github": "🤖", "migrations": "🔄",
}

# 文件图标
FILE_ICONS = {
    ".py": "🐍", ".js": "🟨", ".ts": "🔷", ".jsx": "⚛️", ".tsx": "⚛️",
    ".java": "☕", ".go": "🐹", ".rs": "🦀", ".c": "🔧", ".cpp": "🔧",
    ".rb": "💎", ".php": "🐘", ".html": "🌐", ".css": "🎨", ".json": "📦",
    ".md": "📄", ".yaml": "⚙️", ".yml": "⚙️", ".sql": "🗄️",
}

CODE_EXTS = {".py", ".js", ".ts", ".jsx", ".tsx", ".java", ".go", ".rs",
             ".c", ".cpp", ".rb", ".php"}


def collect_structure(project_dir, max_depth=3):
    """收集项目目录结构"""
    root = Path(project_dir)
    tree = []

    # 递归构建树
    def walk(path, depth):
        if depth > max_depth:
            return []
        entries = []
        for item in sorted(path.iterdir(), key=lambda x: (not x.is_dir(), x.name.lower())):
            if item.name in IGNORE_DIRS or item.name.startswith("."):
                continue
            if item.is_dir():
                children = walk(item, depth + 1)
                entries.append({"type": "dir", "name": item.name, "children": children})
            else:
                if item.suffix in CODE_EXTS or item.suffix in (".md", ".json", ".yaml", ".yml", ".html", ".css"):
                    entries.append({"type": "file", "name": item.name, "ext": item.suffix})
        return entries

    for item in sorted(root.iterdir(), key=lambda x: (not x.is_dir(), x.name.lower())):
        if item.name in IGNORE_DIRS or item.name.startswith("."):
            continue
        if item.is_dir():
            children = walk(item, 1)
            tree.append({"type": "dir", "name": item.name, "children": children})
        else:
            if item.suffix in CODE_EXTS or item.suffix in (".md", ".json", ".yaml", ".yml", ".html", ".css"):
                tree.append({"type": "file", "name": item.name, "ext": item.suffix})

    return tree


def render_tree(tree, prefix=""):
    """渲染树形结构为文本"""
    lines = []
    for i, item in enumerate(tree):
        last = i == len(tree) - 1
        connector = "└── " if last else "├── "
        next_prefix = prefix + ("    " if last else "│   ")

        if item["type"] == "dir":
            icon = DIR_ICONS.get(item["name"], "📁")
            lines.append(f"{prefix}{connector}{icon} {item['name']}/")
            if item.get("children"):
                lines.extend(render_tree(item["children"], next_prefix))
        else:
            icon = FILE_ICONS.get(item["ext"], "📄")
            lines.append(f"{prefix}{connector}{icon} {item['name']}")
    return lines


def count_stats(tree):
    """统计代码文件数和行数"""
    files = 0
    lines = 0

    def walk(nodes):
        nonlocal files, lines
        for node in nodes:
            if node["type"] == "dir":
                walk(node.get("children", []))
            elif node["type"] == "file" and node["ext"] in CODE_EXTS:
                files += 1
    walk(tree)
    return files


def main():
    parser = argparse.ArgumentParser(description="DevFlow 代码地图")
    parser.add_argument("--dir", default=".", help="项目目录")
    parser.add_argument("--depth", type=int, default=3, help="最大深度")
    parser.add_argument("--json", action="store_true", help="JSON 输出")
    args = parser.parse_args()

    project_dir = os.path.abspath(args.dir)
    if not os.path.isdir(project_dir):
        print(f"错误: {project_dir} 不是目录")
        sys.exit(1)

    tree = collect_structure(project_dir, args.depth)

    if args.json:
        print(json.dumps({"project": project_dir, "tree": tree}, ensure_ascii=False, indent=2))
        return

    print(f"🗺️ DevFlow 代码地图: {project_dir}\n")
    for line in render_tree(tree):
        print(line)
    print(f"\n代码文件数: {count_stats(tree)}")


if __name__ == "__main__":
    main()
