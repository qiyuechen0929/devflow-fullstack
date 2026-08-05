#!/usr/bin/env python3
"""
DevFlow - Code Metrics & i18n Extractor (#7, #29)
Usage:
  python metrics-i18n.py --mode metrics --dir .
  python metrics-i18n.py --mode i18n --dir src/ --output zh-CN.json
"""

import argparse, os, re, json
from pathlib import Path
from collections import defaultdict

def compute_metrics(dirpath):
    exts = {".py",".js",".ts",".tsx",".jsx",".java",".go",".c",".cpp",".rs"}
    ignore = {"node_modules",".git","dist","build","__pycache__",".next","target"}
    
    total_lines = 0
    total_files = 0
    total_funcs = 0
    lang_counts = defaultdict(int)
    max_file = ("", 0)
    
    for root, dirs, files in os.walk(dirpath):
        dirs[:] = [d for d in dirs if d not in ignore]
        for f in files:
            if Path(f).suffix in exts:
                fp = os.path.join(root, f)
                try:
                    lines = Path(fp).read_text(encoding="utf-8", errors="ignore").count("\n")
                    total_lines += lines
                    total_files += 1
                    lang_counts[Path(f).suffix] += 1
                    if lines > max_file[1]:
                        max_file = (fp, lines)
                except Exception:
                    pass

    if total_files == 0:
        return "无代码文件"
    
    return f"""# Code Metrics Report

## 概览
- 总文件: {total_files}
- 总行数: {total_lines:,}
- 平均每文件: {total_lines // max(total_files, 1):,} 行

## 语言分布
{chr(10).join(f'- {ext}: {count} 文件' for ext, count in sorted(lang_counts.items()))}

## 最大文件
- `{max_file[0]}`: {max_file[1]:,} 行

## 建议
- {'[!] 有超400行的大文件，建议拆分' if max_file[1] > 400 else '[OK] 文件大小合理'}
- {'[!] 项目较大，考虑模块化' if total_lines > 10000 else '[OK] 项目规模适中'}
"""

def extract_i18n(dirpath):
    exts = {".tsx",".jsx",".ts",".js",".html",".vue"}
    ignore = {"node_modules",".git","dist","build",".next"}
    
    # Match hardcoded Chinese strings
    chinese_pattern = re.compile(r"[\u4e00-\u9fff\u3000-\u303f\uff00-\uffef]+")
    string_pattern = re.compile(r""""([^"]*[\u4e00-\u9fff][^"]*)""" + "|" + """'([^']*[\u4e00-\u9fff][^']*)'""")
    
    strings = defaultdict(list)
    
    for root, dirs, files in os.walk(dirpath):
        dirs[:] = [d for d in dirs if d not in ignore]
        for f in files:
            if Path(f).suffix in exts:
                fp = os.path.join(root, f)
                try:
                    content = Path(fp).read_text(encoding="utf-8", errors="ignore")
                    for i, line in enumerate(content.split("\n"), 1):
                        # Skip comments
                        if line.strip().startswith(("//","#","/*","*")):
                            continue
                        for m in string_pattern.finditer(line):
                            text = m.group(1) or m.group(2)
                            if text and chinese_pattern.search(text):
                                key = text[:40].strip()
                                if key not in strings:
                                    strings[key].append(f"{fp}:{i}")
                except Exception:
                    pass
    
    if not strings:
        return "未发现硬编码中文字符串 [OK]"
    
    result = [f"发现 {len(strings)} 处硬编码中文字符串:\n"]
    for text, locations in strings.items():
        result.append(f"## `{text}`")
        for loc in locations[:3]:
            result.append(f"  - {loc}")
        result.append("")
    
    # Generate JSON template
    json_template = {}
    for i, text in enumerate(strings.keys()):
        key = f"key_{i:03d}"
        json_template[key] = text
    
    result.append("```json")
    result.append(json.dumps(json_template, ensure_ascii=False, indent=2))
    result.append("```")
    
    return "\n".join(result)

def main():
    parser = argparse.ArgumentParser(description="Code Metrics & i18n Extractor")
    parser.add_argument("--mode", choices=["metrics","i18n","all"], default="all")
    parser.add_argument("--dir", default=".")
    args = parser.parse_args()

    if args.mode in ("metrics", "all"):
        print(compute_metrics(args.dir))
    
    if args.mode in ("i18n", "all"):
        print("\n" + extract_i18n(args.dir))

if __name__ == "__main__":
    main()
