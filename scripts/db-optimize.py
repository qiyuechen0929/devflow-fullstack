#!/usr/bin/env python3
"""
DevFlow - Database Query Optimizer (#21)
Usage: python db-optimize.py --file foo.py
"""

import argparse, os, re
from pathlib import Path

ISSUES = [
    # N+1 queries
    (r"for\s+\w+\s+in\s+.*:\s*\n\s*\w+\.\w*query\w*\(|\.find\(|\.filter\(",
     "[!!] N+1 查询: 循环内数据库调用 -> 用 JOIN 或 batch fetch 替代"),
    # Missing index hints
    (r"WHERE\s+\w+\s*=\s*[^;]+(?!.*INDEX)", 
     "[*] 可能缺失索引: WHERE 条件列未建索引 -> 检查查询计划"),
    # SELECT *
    (r"SELECT\s+\*\s+FROM",
     "[*] SELECT *: 取所有列 -> 仅取需要的列，减少传输"),
    # Missing LIMIT
    (r"SELECT\s+(?!.*LIMIT)(?!.*limit)(.{0,200})FROM",
     "[*] 无 LIMIT: 可能返回大量数据 -> 加分页"),
    # String concatenation SQL
    (r"(?:execute|query|raw)\s*\(\s*[\"'][^\"']*\+",
     "[X] SQL 注入风险: 字符串拼接 -> 参数化查询"),
    # Missing transaction
    (r"(?:INSERT|UPDATE|DELETE).*\n\s*(?:INSERT|UPDATE|DELETE)",
     "[!] 多语句写入无事务 -> 可能导致数据不一致"),
    # Eager loading
    (r"\.include\(\{[^}]*include\s*:\s*\{",
     "[*] 嵌套 include: 可能产生大量 JOIN -> 考虑分批加载"),
]

def analyze_file(filepath):
    try:
        content = Path(filepath).read_text(encoding="utf-8", errors="ignore")
        results = []
        for i, line in enumerate(content.split("\n"), 1):
            for pattern, msg in ISSUES:
                m = re.search(pattern, line, re.IGNORECASE)
                if m:
                    results.append(f"{msg} ({filepath}:{i})")
        return results
    except Exception:
        return []

def main():
    parser = argparse.ArgumentParser(description="DB Query Optimizer")
    parser.add_argument("--file")
    parser.add_argument("--dir", default=".")
    args = parser.parse_args()

    exts = {".py",".js",".ts",".tsx",".java",".go",".sql"}
    ignore = {"node_modules",".git","dist","build","__pycache__",".next"}

    all_results = []
    targets = [args.file] if args.file else []
    if not args.file:
        for root, dirs, files in os.walk(args.dir):
            dirs[:] = [d for d in dirs if d not in ignore]
            for f in files:
                if Path(f).suffix in exts:
                    targets.append(os.path.join(root, f))

    for t in targets:
        all_results.extend(analyze_file(t))

    if all_results:
        print(f"发现 {len(all_results)} 个数据库查询问题:\n")
        for r in all_results:
            print(r)
    else:
        print("未发现数据库查询问题 [OK]")

if __name__ == "__main__":
    main()
