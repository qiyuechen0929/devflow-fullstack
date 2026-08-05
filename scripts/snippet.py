#!/usr/bin/env python3
"""
DevFlow - Code Snippet Manager
代码片段保存、搜索、管理
Usage:
  python snippet.py --save --name "react-hook" --file hook.ts --tags react,hooks
  python snippet.py --search --query "useEffect"
  python snippet.py --list
  python snippet.py --show --name "react-hook"
  python snippet.py --export --output snippets.json
  python snippet.py --import --file snippets.json
"""

import argparse
import json
import os
import re
import sys
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional

# 片段存储目录
SNIPPETS_DIR = Path.home() / ".devflow" / "snippets"
SNIPPETS_INDEX = SNIPPETS_DIR / "index.json"


def ensure_snippets_dir():
    """确保片段目录存在"""
    SNIPPETS_DIR.mkdir(parents=True, exist_ok=True)


def load_index() -> Dict:
    """加载索引"""
    if SNIPPETS_INDEX.exists():
        try:
            return json.loads(SNIPPETS_INDEX.read_text(encoding="utf-8"))
        except Exception:
            pass

    return {"snippets": {}, "tags": {}, "created_at": datetime.now().isoformat()}


def save_index(index: Dict):
    """保存索引"""
    ensure_snippets_dir()
    index["updated_at"] = datetime.now().isoformat()
    SNIPPETS_INDEX.write_text(json.dumps(index, indent=2, ensure_ascii=False), encoding="utf-8")


def save_snippet(name: str, content: str, language: str = None, tags: List[str] = None, description: str = "") -> bool:
    """保存代码片段"""
    ensure_snippets_dir()

    # 检测语言
    if not language:
        ext = Path(name).suffix if "." in name else ""
        language_map = {
            ".py": "python", ".js": "javascript", ".ts": "typescript",
            ".jsx": "javascript", ".tsx": "typescript", ".java": "java",
            ".go": "go", ".rs": "rust", ".c": "c", ".cpp": "cpp",
            ".rb": "ruby", ".php": "php", ".html": "html", ".css": "css"
        }
        language = language_map.get(ext, "text")

    # 保存片段文件
    snippet_file = SNIPPETS_DIR / f"{name}.txt"
    snippet_file.write_text(content, encoding="utf-8")

    # 更新索引
    index = load_index()
    index["snippets"][name] = {
        "name": name,
        "file": str(snippet_file),
        "language": language,
        "tags": tags or [],
        "description": description,
        "created_at": datetime.now().isoformat(),
        "updated_at": datetime.now().isoformat(),
        "lines": len(content.split("\n")),
        "chars": len(content)
    }

    # 更新标签索引
    for tag in (tags or []):
        if tag not in index["tags"]:
            index["tags"][tag] = []
        if name not in index["tags"][tag]:
            index["tags"][tag].append(name)

    save_index(index)
    return True


def load_snippet(name: str) -> Optional[Dict]:
    """加载代码片段"""
    index = load_index()

    if name not in index["snippets"]:
        return None

    snippet_info = index["snippets"][name]
    snippet_file = Path(snippet_info["file"])

    if snippet_file.exists():
        content = snippet_file.read_text(encoding="utf-8")
        return {**snippet_info, "content": content}

    return None


def search_snippets(query: str, tag: str = None) -> List[Dict]:
    """搜索代码片段"""
    index = load_index()
    results = []

    for name, info in index["snippets"].items():
        # 按标签搜索
        if tag and tag not in info.get("tags", []):
            continue

        # 按名称、描述、内容搜索
        snippet = load_snippet(name)
        if not snippet:
            continue

        searchable = f"{name} {info.get('description', '')} {snippet.get('content', '')}".lower()

        if query.lower() in searchable:
            results.append({
                "name": name,
                "language": info.get("language"),
                "tags": info.get("tags", []),
                "description": info.get("description"),
                "lines": info.get("lines"),
                "preview": snippet.get("content", "")[:200]
            })

    return results


def list_snippets(tag: str = None, language: str = None) -> List[Dict]:
    """列出代码片段"""
    index = load_index()
    results = []

    for name, info in index["snippets"].items():
        # 按标签过滤
        if tag and tag not in info.get("tags", []):
            continue

        # 按语言过滤
        if language and info.get("language") != language:
            continue

        results.append({
            "name": name,
            "language": info.get("language"),
            "tags": info.get("tags", []),
            "description": info.get("description"),
            "lines": info.get("lines"),
            "created_at": info.get("created_at")
        })

    return sorted(results, key=lambda x: x.get("created_at", ""), reverse=True)


def delete_snippet(name: str) -> bool:
    """删除代码片段"""
    index = load_index()

    if name not in index["snippets"]:
        return False

    # 删除文件
    snippet_file = Path(index["snippets"][name]["file"])
    if snippet_file.exists():
        snippet_file.unlink()

    # 从标签索引中移除
    for tag, snippets in index.get("tags", {}).items():
        if name in snippets:
            snippets.remove(name)

    # 从索引中移除
    del index["snippets"][name]
    save_index(index)

    return True


def export_snippets(output_path: str, tag: str = None) -> bool:
    """导出代码片段"""
    index = load_index()
    snippets = {}

    for name, info in index["snippets"].items():
        if tag and tag not in info.get("tags", []):
            continue

        snippet = load_snippet(name)
        if snippet:
            snippets[name] = {
                "content": snippet.get("content"),
                "language": info.get("language"),
                "tags": info.get("tags", []),
                "description": info.get("description")
            }

    try:
        Path(output_path).write_text(json.dumps(snippets, indent=2, ensure_ascii=False), encoding="utf-8")
        return True
    except Exception as e:
        print(f"Error exporting: {e}", file=sys.stderr)
        return False


def import_snippets(input_path: str) -> int:
    """导入代码片段"""
    try:
        content = Path(input_path).read_text(encoding="utf-8")
        snippets = json.loads(content)

        count = 0
        for name, info in snippets.items():
            if save_snippet(
                name=name,
                content=info.get("content", ""),
                language=info.get("language"),
                tags=info.get("tags", []),
                description=info.get("description", "")
            ):
                count += 1

        return count
    except Exception as e:
        print(f"Error importing: {e}", file=sys.stderr)
        return 0


def list_tags() -> List[Dict]:
    """列出所有标签"""
    index = load_index()
    tags = []

    for tag, snippets in index.get("tags", {}).items():
        tags.append({
            "name": tag,
            "count": len(snippets)
        })

    return sorted(tags, key=lambda x: x["count"], reverse=True)


def format_snippet(snippet: Dict, format: str = "text") -> str:
    """格式化片段信息"""
    if format == "json":
        return json.dumps(snippet, indent=2, ensure_ascii=False)

    lines = []
    lines.append("=" * 60)
    lines.append(f"Snippet: {snippet.get('name')}")
    lines.append("=" * 60)
    lines.append(f"Language: {snippet.get('language', 'N/A')}")
    lines.append(f"Tags: {', '.join(snippet.get('tags', []))}")
    lines.append(f"Description: {snippet.get('description', 'N/A')}")
    lines.append(f"Lines: {snippet.get('lines', 0)}")
    lines.append(f"Created: {snippet.get('created_at', 'N/A')}")
    lines.append("")
    lines.append("[Content]")
    lines.append("-" * 60)
    lines.append(snippet.get("content", ""))
    lines.append("-" * 60)

    return "\n".join(lines)


def format_snippets_list(snippets: List[Dict], format: str = "text") -> str:
    """格式化片段列表"""
    if format == "json":
        return json.dumps(snippets, indent=2, ensure_ascii=False)

    lines = []
    lines.append("=" * 60)
    lines.append("DevFlow Code Snippets")
    lines.append("=" * 60)
    lines.append("")

    if not snippets:
        lines.append("No snippets found.")
    else:
        for snippet in snippets:
            tags = ", ".join(snippet.get("tags", []))
            lines.append(f"- {snippet['name']} [{snippet.get('language', '?')}]")
            if tags:
                lines.append(f"  Tags: {tags}")
            if snippet.get("description"):
                lines.append(f"  Desc: {snippet['description']}")
            lines.append(f"  Lines: {snippet.get('lines', 0)}")
            lines.append("")

    lines.append(f"Total: {len(snippets)} snippets")
    lines.append("=" * 60)

    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser(
        description="DevFlow Code Snippet Manager",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Save snippet from file
  python snippet.py --save --name "react-hook" --file hook.ts --tags react,hooks

  # Save snippet from stdin
  echo "console.log('test')" | python snippet.py --save --name "log" --language javascript

  # Search snippets
  python snippet.py --search --query "useEffect"

  # List all snippets
  python snippet.py --list

  # List by tag
  python snippet.py --list --tag react

  # Show snippet
  python snippet.py --show --name "react-hook"

  # Export snippets
  python snippet.py --export --output snippets.json

  # Import snippets
  python snippet.py --import --file snippets.json

  # Delete snippet
  python snippet.py --delete --name "react-hook"
        """
    )

    parser.add_argument("--save", action="store_true", help="Save snippet")
    parser.add_argument("--search", action="store_true", help="Search snippets")
    parser.add_argument("--list", action="store_true", help="List snippets")
    parser.add_argument("--show", action="store_true", help="Show snippet")
    parser.add_argument("--delete", action="store_true", help="Delete snippet")
    parser.add_argument("--export", action="store_true", help="Export snippets")
    parser.add_argument("--import", dest="import_snippets", action="store_true", help="Import snippets")
    parser.add_argument("--tags", action="store_true", help="List tags")

    parser.add_argument("--name", "-n", help="Snippet name")
    parser.add_argument("--file", "-f", help="Source file")
    parser.add_argument("--query", "-q", help="Search query")
    parser.add_argument("--tag", "-t", help="Filter by tag")
    parser.add_argument("--language", "-l", help="Programming language")
    parser.add_argument("--description", help="Snippet description")
    parser.add_argument("--tag-list", help="Comma-separated tags")
    parser.add_argument("--format", choices=["text", "json"], default="text", help="Output format")
    parser.add_argument("--output", "-o", help="Output file path")

    args = parser.parse_args()

    # 保存片段
    if args.save:
        if not args.name:
            print("Error: --name is required for --save", file=sys.stderr)
            sys.exit(1)

        # 从文件或stdin读取内容
        if args.file:
            content = Path(args.file).read_text(encoding="utf-8")
        elif not sys.stdin.isatty():
            content = sys.stdin.read()
        else:
            print("Error: --file or stdin input required", file=sys.stderr)
            sys.exit(1)

        tags = args.tag_list.split(",") if args.tag_list else []

        if save_snippet(args.name, content, args.language, tags, args.description or ""):
            print(f"Snippet '{args.name}' saved.")
        else:
            print("Error saving snippet.", file=sys.stderr)
            sys.exit(1)
        return

    # 搜索片段
    if args.search:
        if not args.query:
            print("Error: --query is required for --search", file=sys.stderr)
            sys.exit(1)

        results = search_snippets(args.query, args.tag)
        print(format_snippets_list(results, args.format))
        return

    # 列出片段
    if args.list:
        snippets = list_snippets(args.tag, args.language)
        print(format_snippets_list(snippets, args.format))
        return

    # 显示片段
    if args.show:
        if not args.name:
            print("Error: --name is required for --show", file=sys.stderr)
            sys.exit(1)

        snippet = load_snippet(args.name)
        if snippet:
            print(format_snippet(snippet, args.format))
        else:
            print(f"Snippet '{args.name}' not found.")
        return

    # 删除片段
    if args.delete:
        if not args.name:
            print("Error: --name is required for --delete", file=sys.stderr)
            sys.exit(1)

        if delete_snippet(args.name):
            print(f"Snippet '{args.name}' deleted.")
        else:
            print(f"Snippet '{args.name}' not found.")
        return

    # 导出片段
    if args.export:
        output = args.output or "snippets.json"
        if export_snippets(output, args.tag):
            print(f"Snippets exported to: {output}")
        return

    # 导入片段
    if args.import_snippets:
        if not args.file:
            print("Error: --file is required for --import", file=sys.stderr)
            sys.exit(1)

        count = import_snippets(args.file)
        print(f"Imported {count} snippets.")
        return

    # 列出标签
    if args.tags:
        tags = list_tags()
        print("Tags:")
        for tag in tags:
            print(f"  - {tag['name']}: {tag['count']} snippets")
        return

    # 默认显示帮助
    parser.print_help()


if __name__ == "__main__":
    main()
