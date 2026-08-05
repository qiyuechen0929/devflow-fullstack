#!/usr/bin/env python3
"""
DevFlow - Code Similarity Detector
检测重复代码
Usage:
  python similarity.py --dir src/
  python similarity.py --file main.py
  python similarity.py --dir src/ --threshold 0.8
  python similarity.py --dir src/ --output report.json
"""

import argparse
import hashlib
import json
import re
import sys
from collections import defaultdict
from pathlib import Path
from typing import Dict, List, Set, Tuple


def normalize_code(content: str) -> str:
    """规范化代码（移除注释、空格、变量名）"""
    lines = content.split("\n")
    normalized = []

    for line in lines:
        stripped = line.strip()

        # 跳过空行和注释
        if not stripped or stripped.startswith(("#", "//", "/*", "*", "<!--")):
            continue

        # 移除字符串内容
        stripped = re.sub(r'"[^"]*"', '""', stripped)
        stripped = re.sub(r"'[^']*'", "''", stripped)

        # 移除变量名（保留关键字）
        # 这是一个简化的处理
        keywords = {"if", "else", "for", "while", "def", "class", "return", "import", "from",
                    "function", "var", "let", "const", "public", "private", "protected", "static"}
        words = stripped.split()
        normalized_words = []
        for word in words:
            if word in keywords:
                normalized_words.append(word)
            else:
                normalized_words.append("X")

        normalized.append(" ".join(normalized_words))

    return "\n".join(normalized)


def calculate_hash(content: str) -> str:
    """计算代码哈希"""
    normalized = normalize_code(content)
    return hashlib.md5(normalized.encode()).hexdigest()


def extract_code_blocks(content: str, min_lines: int = 5) -> List[Tuple[int, str]]:
    """提取代码块"""
    lines = content.split("\n")
    blocks = []

    i = 0
    while i < len(lines):
        # 跳过空行和注释
        if not lines[i].strip() or lines[i].strip().startswith(("#", "//", "/*", "*")):
            i += 1
            continue

        # 提取连续的代码行
        block_start = i
        block_lines = []

        while i < len(lines) and (lines[i].strip() and not lines[i].strip().startswith(("#", "//", "/*", "*"))):
            block_lines.append(lines[i])
            i += 1

        if len(block_lines) >= min_lines:
            blocks.append((block_start + 1, "\n".join(block_lines)))

        i += 1

    return blocks


def calculate_similarity(code1: str, code2: str) -> float:
    """计算两段代码的相似度"""
    # 规范化
    norm1 = normalize_code(code1)
    norm2 = normalize_code(code2)

    # 如果完全相同
    if norm1 == norm2:
        return 1.0

    # 使用行级别的比较
    lines1 = set(norm1.split("\n"))
    lines2 = set(norm2.split("\n"))

    if not lines1 or not lines2:
        return 0.0

    # 计算 Jaccard 相似度
    intersection = lines1 & lines2
    union = lines1 | lines2

    return len(intersection) / len(union)


def find_duplicates_in_file(file_path: str, min_lines: int = 5) -> List[Dict]:
    """在单个文件中查找重复"""
    try:
        content = Path(file_path).read_text(encoding="utf-8", errors="ignore")
        blocks = extract_code_blocks(content, min_lines)

        duplicates = []
        seen_hashes = {}

        for line_num, block in blocks:
            block_hash = calculate_hash(block)

            if block_hash in seen_hashes:
                duplicates.append({
                    "file": file_path,
                    "line": line_num,
                    "duplicate_of_line": seen_hashes[block_hash],
                    "lines": len(block.split("\n")),
                    "hash": block_hash
                })
            else:
                seen_hashes[block_hash] = line_num

        return duplicates
    except Exception:
        return []


def find_duplicates_across_files(directory: str, min_lines: int = 5, threshold: float = 0.8) -> List[Dict]:
    """跨文件查找重复"""
    dir_path = Path(directory)
    all_blocks = []

    # 收集所有代码块
    for file_path in dir_path.rglob("*"):
        if any(part.startswith(".") or part in ("node_modules", "vendor", "dist", "build", "__pycache__")
               for part in file_path.parts):
            continue

        if file_path.suffix in (".py", ".js", ".ts", ".jsx", ".tsx", ".java", ".go") and file_path.is_file():
            try:
                content = file_path.read_text(encoding="utf-8", errors="ignore")
                blocks = extract_code_blocks(content, min_lines)

                for line_num, block in blocks:
                    all_blocks.append({
                        "file": str(file_path),
                        "line": line_num,
                        "block": block,
                        "hash": calculate_hash(block)
                    })
            except Exception:
                continue

    # 查找重复
    duplicates = []
    hash_groups = defaultdict(list)

    for block_info in all_blocks:
        hash_groups[block_info["hash"]].append(block_info)

    # 找出有多个块的哈希
    for block_hash, blocks in hash_groups.items():
        if len(blocks) > 1:
            for i in range(len(blocks)):
                for j in range(i + 1, len(blocks)):
                    similarity = calculate_similarity(blocks[i]["block"], blocks[j]["block"])

                    if similarity >= threshold:
                        duplicates.append({
                            "file1": blocks[i]["file"],
                            "line1": blocks[i]["line"],
                            "file2": blocks[j]["file"],
                            "line2": blocks[j]["line"],
                            "lines": len(blocks[i]["block"].split("\n")),
                            "similarity": similarity
                        })

    return duplicates


def format_report(duplicates: List[Dict], format: str = "text") -> str:
    """格式化报告"""
    if format == "json":
        return json.dumps({
            "total": len(duplicates),
            "duplicates": duplicates
        }, indent=2, ensure_ascii=False)

    lines = []
    lines.append("=" * 60)
    lines.append("DevFlow Code Similarity Detector")
    lines.append("=" * 60)
    lines.append("")
    lines.append(f"Duplicates found: {len(duplicates)}")
    lines.append("")

    if duplicates:
        lines.append("[Duplicates]")
        lines.append("-" * 60)

        for i, dup in enumerate(duplicates[:20], 1):
            if "file1" in dup:
                # 跨文件重复
                lines.append(f"{i}. {Path(dup['file1']).name}:{dup['line1']} <-> {Path(dup['file2']).name}:{dup['line2']}")
                lines.append(f"   Lines: {dup['lines']}, Similarity: {dup['similarity']:.1%}")
            else:
                # 文件内重复
                lines.append(f"{i}. {Path(dup['file']).name}:{dup['line']} <-> line {dup['duplicate_of_line']}")
                lines.append(f"   Lines: {dup['lines']}")
            lines.append("")
    else:
        lines.append("[OK] No duplicates found!")

    lines.append("=" * 60)
    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser(
        description="DevFlow Code Similarity Detector",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Find duplicates in directory
  python similarity.py --dir src/

  # Find duplicates in single file
  python similarity.py --file main.py

  # Set similarity threshold
  python similarity.py --dir src/ --threshold 0.9

  # Set minimum block size
  python similarity.py --dir src/ --min-lines 10

  # Output as JSON
  python similarity.py --dir src/ --format json
        """
    )

    parser.add_argument("--dir", "-d", help="Directory to scan")
    parser.add_argument("--file", "-f", help="Single file to analyze")
    parser.add_argument("--threshold", "-t", type=float, default=0.8,
                        help="Similarity threshold (0-1, default: 0.8)")
    parser.add_argument("--min-lines", type=int, default=5,
                        help="Minimum lines for a code block (default: 5)")
    parser.add_argument("--format", choices=["text", "json"], default="text", help="Output format")
    parser.add_argument("--output", "-o", help="Output file path")

    args = parser.parse_args()

    if not args.dir and not args.file:
        print("Error: --dir or --file is required", file=sys.stderr)
        sys.exit(1)

    # 查找重复
    if args.file:
        duplicates = find_duplicates_in_file(args.file, args.min_lines)
    else:
        duplicates = find_duplicates_across_files(args.dir, args.min_lines, args.threshold)

    # 生成报告
    report = format_report(duplicates, args.format)

    # 输出
    if args.output:
        Path(args.output).write_text(report, encoding="utf-8")
        print(f"Report saved to: {args.output}")
    else:
        print(report)


if __name__ == "__main__":
    main()
