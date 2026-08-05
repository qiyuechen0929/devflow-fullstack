#!/usr/bin/env python3
"""
DevFlow - A11y Checker for HTML/React/JSX
Usage: python a11y.py --file component.tsx
"""

import argparse, os, re
from pathlib import Path

CHECKS = [
    (r"<img\s+(?![^>]*\balt\b)[^>]*>", "[X] 图片缺少 alt 属性 -> <img alt='描述' ...>"),
    (r"<input\s+(?![^>]*\baria-label\b)(?![^>]*\bid=['\"]\w+['\"]\s*<label)[^>]*>", "[!]  input 缺少 label 关联 -> 用 <label> 或 aria-label"),
    (r"onClick\s*=\s*\{[^}]*\}\s*(?![^>]*\brole\b)", "[!]  onClick 在非交互元素上 -> 加 role='button' tabIndex={0}"),
    (r"<div\s+onClick", "[!]  div 代替 button -> 用 <button> 而非 <div onClick>"),
    (r"color:\s*#[0-9a-fA-F]{6}\s*;\s*background-color:\s*#[0-9a-fA-F]{6}", "[!]  检查文字/背景颜色对比度 ≥4.5:1"),
    (r"font-size:\s*(\d{1,2})px", lambda m: f"[!]  字体 {m.group(1)}px (<16px) -> 不建议小于16px" if int(m.group(1)) < 14 else ""),
    (r"tabIndex\s*=\s*\{?(-?\d+)\}?", lambda m: f"[!]  tabIndex={m.group(1)} -> 避免自定义 tabIndex" if int(m.group(1)) > 0 else ""),
    (r"<html\s+(?![^>]*\blang\b)", "[X] html 缺少 lang 属性 -> <html lang='zh-CN'>"),
    (r"<a\s+(?![^>]*\bhref\b)[^>]*>", "[!]  a 标签缺少 href -> 如果是按钮用 <button>"),
]

def check_file(filepath):
    try:
        content = Path(filepath).read_text(encoding="utf-8", errors="ignore")
        results = []
        for pattern, message in CHECKS:
            for i, line in enumerate(content.split("\n"), 1):
                m = re.search(pattern, line)
                if m:
                    if callable(message):
                        msg = message(m)
                        if msg:
                            results.append(f"{filepath}:{i} {msg}")
                    else:
                        results.append(f"{filepath}:{i} {message}")
        return results
    except Exception:
        return []

def main():
    parser = argparse.ArgumentParser(description="A11y Checker")
    parser.add_argument("--file")
    parser.add_argument("--dir", default=".")
    args = parser.parse_args()

    exts = {".html",".tsx",".jsx",".vue",".svelte"}
    ignore = {"node_modules",".git","dist","build",".next"}

    all_results = []
    if args.file:
        all_results = check_file(args.file)
    else:
        for root, dirs, files in os.walk(args.dir):
            dirs[:] = [d for d in dirs if d not in ignore]
            for f in files:
                if Path(f).suffix in exts:
                    all_results.extend(check_file(os.path.join(root, f)))

    if all_results:
        print(f"发现 {len(all_results)} 个无障碍问题:\n")
        for r in all_results:
            print(r)
    else:
        print("未发现明显无障碍问题 [OK]")

if __name__ == "__main__":
    main()
