#!/usr/bin/env python3
"""
DevFlow Fullstack - Documentation Generator
Usage:
  python docgen.py --file foo.py --mode inline|function|api|readme
  python docgen.py --dir src/ --mode all
"""

import argparse, os, re
from pathlib import Path
from datetime import datetime

def generate_inline_doc(filepath):
    """Add inline comments for complex logic"""
    content = Path(filepath).read_text(encoding="utf-8", errors="ignore")
    lines = content.split("\n")
    new_lines = []
    for i, line in enumerate(lines):
        new_lines.append(line)
        # Add comment before complex conditions
        if re.search(r"if\s+.*\band\b.*\bor\b|if\s+.*>.*<|if\s+.*!\(", line) and "//" not in line and "#" not in line:
            new_lines.insert(len(new_lines)-1, "  // 复合条件判断 -> 考虑提取为有意义的布尔变量")
        # Add comment on regex
        if re.search(r"re\.(match|search|findall|sub)\(", line) and "//" not in line:
            new_lines.insert(len(new_lines)-1, f"  // 正则匹配: 考虑添加注释解释匹配规则")
    return "\n".join(new_lines)

def generate_function_doc(filepath):
    """Generate function-level documentation"""
    content = Path(filepath).read_text(encoding="utf-8", errors="ignore")
    lines = content.split("\n")
    ext = Path(filepath).suffix
    result = []
    in_func = False
    func_name = ""
    params = []

    for i, line in enumerate(lines):
        # Detect function/method definitions
        m = re.match(r"(?:def|function|func|public|private|protected)\s+(\w+)\s*\(([^)]*)\)", line.strip())
        if m:
            func_name = m.group(1)
            params = [p.strip() for p in m.group(2).split(",") if p.strip()]
            result.append(f"\n### `{func_name}()`")
            result.append("")
            if params:
                result.append("| 参数 | 说明 |")
                result.append("|------|------|")
                for p in params:
                    result.append(f"| `{p}` | TODO |")
                result.append("")
            result.append("**功能**: TODO")
            result.append("")
            result.append("**返回值**: TODO")
            result.append("")

    return "\n".join(result)

def generate_readme(dirpath):
    """Generate README snippet"""
    name = Path(dirpath).resolve().name
    now = datetime.now().strftime("%Y-%m-%d")
    files = list(Path(dirpath).rglob("*"))
    exts = set(f.suffix for f in files if f.suffix)
    lang_map = {".py":"Python", ".js":"JavaScript", ".ts":"TypeScript", ".tsx":"React+TS",
                ".jsx":"React", ".java":"Java", ".go":"Go", ".rs":"Rust", ".c":"C", ".cpp":"C++"}
    langs = [lang_map.get(e, e) for e in exts if e in lang_map]

    return f"""# {name}

> 最后更新: {now}

## 速览

- **语言**: {', '.join(langs) if langs else 'N/A'}
- **类型**: TODO (CLI / Web / Library / Mobile)

## 安装

```bash
# TODO: 安装步骤
```

## 使用

```bash
# TODO: 使用示例
```

## 结构

```
{name}/
├── src/          # 源代码
├── tests/        # 测试
└── README.md     # 本文件
```

## 贡献

TODO: 贡献指南
"""

def main():
    parser = argparse.ArgumentParser(description="DevFlow Documentation Generator")
    parser.add_argument("--file")
    parser.add_argument("--dir")
    parser.add_argument("--mode", default="inline",
                       choices=["inline","function","readme","all"])
    parser.add_argument("--output", help="输出文件路径")
    args = parser.parse_args()

    target = args.file or args.dir
    if not target:
        print("请指定 --file 或 --dir")

    results = []
    if args.mode in ("inline", "all"):
        results.append("/* === 行内注释建议 === */")
        if args.file:
            results.append(f"文件: {args.file}")
            results.append("（对复杂逻辑添加解释性注释）")
        else:
            results.append(f"目录: {args.dir}")

    if args.mode in ("function", "all"):
        results.append("\n/* === 函数文档 === */")
        if args.file:
            results.append(generate_function_doc(args.file))
        else:
            for root, dirs, files in os.walk(target):
                dirs[:] = [d for d in dirs if d not in {"node_modules",".git","dist","build"}]
                for f in files[:5]:
                    if f.endswith((".py",".js",".ts",".tsx",".java")):
                        results.append(generate_function_doc(os.path.join(root, f)))

    if args.mode in ("readme", "all"):
        results.append("\n/* === README 模板 === */")
        results.append(generate_readme(target if not args.file else Path(args.file).parent))

    output = "\n".join(results)
    if args.output:
        Path(args.output).write_text(output, encoding="utf-8")
        print(f"已输出到 {args.output}")
    else:
        print(output)

if __name__ == "__main__":
    main()
