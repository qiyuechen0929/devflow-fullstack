#!/usr/bin/env python3
"""
DevFlow Fullstack - Clean Debug Markers
Usage: python clean-debug.py --dir src/
"""

import argparse, os, re
from pathlib import Path

def clean_file(filepath, dry_run=False):
    content = Path(filepath).read_text(encoding="utf-8", errors="ignore")
    # Remove lines containing DEVMARK
    cleaned = "\n".join([
        line for line in content.split("\n")
    ]).strip() + "\n"

    if content != cleaned:
        if dry_run:
            print(f"  [预览] {filepath} - 将移除 {content.count(chr(10)) - cleaned.count(chr(10))} 行")
        else:
            Path(filepath).write_text(cleaned, encoding="utf-8")
            print(f"  [已清理] {filepath}")

def main():
    parser = argparse.ArgumentParser(description="Clean DevFlow debug markers")
    parser.add_argument("--dir", default=".")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    exts = {".py",".js",".ts",".tsx",".jsx",".java",".go",".c",".cpp",".rs",".rb",".php"}
    ignore = {"node_modules",".git","dist","build","__pycache__",".next","target","vendor"}

    for root, dirs, files in os.walk(args.dir):
        dirs[:] = [d for d in dirs if d not in ignore]
        for f in files:
            if Path(f).suffix in exts:
                clean_file(os.path.join(root, f), args.dry_run)

    print("\n完成！")

if __name__ == "__main__":
    main()
