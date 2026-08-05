#!/usr/bin/env python3
"""
DevFlow Fullstack - Syntax & Language Migration
Usage:
  python migrate.py --from py2 --to py3 --file foo.py
  python migrate.py --from es5 --to es6 --dir src/
  python migrate.py --lang c_to_java --file main.c
"""

import argparse, os, re
from pathlib import Path

# ─── Python 2 -> 3 ───
PY2_TO_PY3 = [
    (r"print\s+([^(].*)", r"print(\1)"),
    (r"xrange\(", "range("),
    (r"raw_input\(", "input("),
    (r"\.has_key\((.+)\)", r"(\1 in "),
    (r"\bunicode\(", "str("),
    (r"\.iteritems\(\)", ".items()"),
    (r"\.itervalues\(\)", ".values()"),
    (r"\.iterkeys\(\)", ".keys()"),
    (r"except\s+(\w+)\s*,\s*(\w+)", r"except \1 as \2"),
    (r"raise\s+(\w+)\s*,\s*(\w+)", r"raise \1(\2)"),
]

# ─── ES5 -> ES6+ ───

# ─── Java 8 → 17 ───
JAVA8_TO_JAVA17 = [
    (r"List<(\w+)>\s+(\w+)\s*=\s*new\s+ArrayList<>\(\)", r"var \2 = new ArrayList<\1>()"),
    (r"Map<(\w+),\s*(\w+)>\s+(\w+)\s*=\s*new\s+HashMap<>\(\)", r"var \3 = new HashMap<\1, \2>()"),
    (r"(\w+)\s+(\w+)\s*=\s*(\w+)\.stream\(\).*\.collect\(Collectors\.toList\(\)\)", r"var \2 = \3.stream().toList()"),
    (r"if\s*\((\w+)\s*!=\s*null\s*&&\s*!(\w+)\.isEmpty\(\)\)", r"if (\1 != null && !\1.isEmpty())"),
    (r"switch\s*\((\w+)\)\s*\{", r"switch (\1) {  // Consider: Java 17 pattern matching switch"),
    (r'LocalDate\.parse\(([^)]+)\)', r'LocalDate.parse(\1)  // Java 17: use java.time'),
]

# ─── C → Python (conceptual, structural only) ───
C_TO_PYTHON = [
    (r"#include\s+<(.+)>", r"# C include <\1> -> Python: import relevant_module"),
    (r"int\s+main\s*\(\s*\)\s*\{", r"def main():"),
    (r"printf\s*\(([^;]+)\)\s*;", r"print(\1)  # printf -> print()"),
    (r"scanf\s*\(([^;]+)\)\s*;", r"# scanf(\1) -> input()"),
    (r"//\s*(.*)", r"# \1"),
]
ES5_TO_ES6 = [
    (r"var\s+(\w+)\s*=\s*require\(([^)]+)\)", r"import \1 from \2"),
    (r"var\s+\{([^}]+)\}\s*=\s*require\(([^)]+)\)", r"import {\1} from \2"),
    (r"module\.exports\s*=\s*(\w+)", r"export default \1"),
    (r"function\s+(\w+)\(([^)]*)\)\s*\{", r"const \1 = (\2) => {"),
    (r"(\w+)\.bind\(this\)", r"\1"),
    (r"var\s+that\s*=\s*this", r"// removed (use arrow functions)"),
]

def apply_rules(content, rules):
    for pattern, replacement in rules:
        content = re.sub(pattern, replacement, content)
    return content

def process_file(filepath, rules, dry_run=False):
    try:
        content = Path(filepath).read_text(encoding="utf-8")
        new_content = apply_rules(content, rules)

        if new_content == content:
            print(f"  {filepath}: 无需转换")
            return

        if dry_run:
            print(f"\n{'='*60}")
            print(f"文件: {filepath}")
            print(f"{'='*60}")
            old_lines = content.split("\n")
            new_lines = new_content.split("\n")
            for i, (old, new) in enumerate(zip(old_lines, new_lines)):
                if old != new:
                    print(f"  第{i+1}行:")
                    print(f"    - {old}")
                    print(f"    + {new}")
        else:
            Path(filepath).write_text(new_content, encoding="utf-8")
            print(f"  {filepath}: 已转换")
    except Exception as e:
        print(f"  {filepath}: 错误 - {e}")

def main():
    parser = argparse.ArgumentParser(description="DevFlow Syntax Migration")
    parser.add_argument("--from", dest="from_lang", required=True,
                       choices=["py2","es5","c","java8","sql_oracle","sql_mysql"])
    parser.add_argument("--to", dest="to_lang", required=True,
                       choices=["py3","es6","java","python","go","java17","sql_mysql","sql_pg"])
    parser.add_argument("--file")
    parser.add_argument("--dir")
    parser.add_argument("--dry-run", action="store_true", help="仅预览不改动")
    args = parser.parse_args()

    key = f"{getattr(args,'from_lang')}_to_{args.to_lang}"
    rules_map = {
        "java8_to_java17": JAVA8_TO_JAVA17,
        "c_to_python": C_TO_PYTHON,
        "py2_to_py3": PY2_TO_PY3,
        "es5_to_es6": ES5_TO_ES6,
    }

    if key not in rules_map:
        print(f"暂不支持 {getattr(args,'from_lang')} -> {args.to_lang} 的自动转换")
        print("可手动描述需求，Skills 会指导分步转换")
        return

    rules = rules_map[key]
    target = args.file or args.dir
    if not target:
        print("请指定 --file 或 --dir")
        return

    if args.file:
        process_file(target, rules, args.dry_run)
    else:
        exts = {".py": [".py"], ".js": [".js",".jsx",".ts",".tsx"]}.get(
            key.split("_")[0], [".py",".js",".ts"])
        for root, dirs, files in os.walk(target):
            dirs[:] = [d for d in dirs if d not in {"node_modules",".git","__pycache__","dist","build"}]
            for f in files:
                if any(f.endswith(e) for e in exts):
                    process_file(os.path.join(root, f), rules, args.dry_run)

if __name__ == "__main__":
    main()
