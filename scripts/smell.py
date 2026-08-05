#!/usr/bin/env python3
"""
DevFlow - Code Smell Detector

Python 文件使用 AST 分析（真实函数/类/参数/命名检测）；其他语言回退到正则启发式。

Usage: python smell.py --file foo.py
       python smell.py --dir src/
"""

import argparse
import ast
import os
import re
from pathlib import Path

PY_EXTS = {".py", ".pyw"}

# ============================================================
# Python AST 坏味道检测
# ============================================================

BAD_PARAM_NAMES = {"a", "b", "c", "d", "e", "x", "y", "z", "tmp", "temp", "var", "val"}
PARAM_LIMIT = 5
FUNC_LINE_LIMIT = 80
FILE_LINE_LIMIT = 400
MAX_NESTING = 4


NESTING_STMTS = (ast.If, ast.For, ast.While, ast.With, ast.Try,
                 ast.AsyncFor, ast.AsyncWith, ast.Match)


def _control_nesting(node):
    """统计控制流嵌套深度：只沿块结构语句递归（if/for/while/with/try），不含表达式"""
    max_depth = [0]

    def walk(n, depth):
        for child in ast.iter_child_nodes(n):
            if isinstance(child, NESTING_STMTS):
                max_depth[0] = max(max_depth[0], depth + 1)
                walk(child, depth + 1)
            elif isinstance(child, (ast.FunctionDef, ast.AsyncFunctionDef)):
                # 不跨函数递归（子函数单独统计）
                continue
            elif isinstance(child, ast.stmt):
                walk(child, depth)

    walk(node, 0)
    return max_depth[0]


def _is_docstring(stmt):
    return (isinstance(stmt, ast.Expr)
            and isinstance(stmt.value, ast.Constant)
            and isinstance(stmt.value.value, str))


def _real_body(body):
    if body and _is_docstring(body[0]):
        return body[1:]
    return body


def _has_meaningful_statements(body):
    real = _real_body(body)
    return bool(real) and not all(isinstance(s, ast.Pass) for s in real)


def smell_ast(filepath, content):
    """Python AST 坏味道检测，返回 [(lineno|None, name, advice)]"""
    try:
        tree = ast.parse(content)
    except SyntaxError:
        return []  # 语法错误由 review.py 处理
    lines = content.split("\n")
    results = []

    def add(lineno, name, advice):
        results.append((lineno, name, advice))

    # 文件过大
    if len(lines) > FILE_LINE_LIMIT:
        add(None, "long_file", f"文件过大 ({len(lines)}行) -> 拆分模块 (阈值 {FILE_LINE_LIMIT})")

    for node in ast.walk(tree):
        # 函数过长
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            flen = (node.end_lineno or node.lineno) - node.lineno + 1
            if flen > FUNC_LINE_LIMIT:
                add(node.lineno, "long_method",
                    f"函数 `{node.name}` 过长 ({flen}行) -> 拆分为多个小函数 (阈值 {FUNC_LINE_LIMIT})")

        # 参数过多
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            params = [a.arg for a in node.args.args if a.arg != "self"]
            if len(params) > PARAM_LIMIT:
                add(node.lineno, "long_param",
                    f"函数 `{node.name}` 参数过多 ({len(params)}个) -> 用对象/struct 封装 (阈值 {PARAM_LIMIT})")

        # 过小的类
        if isinstance(node, ast.ClassDef):
            real = [s for s in _real_body(node.body)
                    if isinstance(s, (ast.FunctionDef, ast.AsyncFunctionDef))]
            if _has_meaningful_statements(node.body) and len(real) < 1:
                add(node.lineno, "lazy_class",
                    f"类 `{node.name}` 过小 (无方法) -> 合并到相关类或删除")

        # 嵌套过深
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            depth = _control_nesting(node)
            if depth > MAX_NESTING:
                add(node.lineno, "deep_nesting",
                    f"函数 `{node.name}` 嵌套深度 {depth} -> 建议 ≤{MAX_NESTING}，使用 early return 或提取函数")

        # 魔法数字（赋值/比较中出现的 2+ 位数字常量）
        if isinstance(node, ast.Assign) and isinstance(node.value, ast.Constant) \
           and isinstance(node.value.value, int) and abs(node.value.value) >= 10 \
           and abs(node.value.value) not in (200, 201, 400, 401, 403, 404, 500):
            add(node.lineno, "magic_number",
                f"魔法数字 {node.value.value} -> 提取为命名常量")

        # 通配符导入
        if isinstance(node, ast.ImportFrom) and any(n.name == "*" for n in node.names):
            add(node.lineno, "inappropriate_intimacy",
                "通配符导入 -> 明确导入所需")

        # 裸 except
        if isinstance(node, ast.ExceptHandler) and node.type is None:
            add(node.lineno, "bare_except",
                "裸 except -> 指定具体异常类型")

        # 无意义/单字母变量名
        if isinstance(node, ast.Name) and isinstance(node.ctx, ast.Store) \
           and node.id in BAD_PARAM_NAMES:
            add(node.lineno, "bad_name",
                f"无意义变量名 `{node.id}` -> 用描述性名称")

        # 可疑的重复 is/== 混用：`is not None` 后紧跟 `==`
        if isinstance(node, ast.Compare) and len(node.ops) == 1 \
           and isinstance(node.ops[0], ast.Is) \
           and isinstance(node.comparators[0], ast.Constant) \
           and node.comparators[0].value is None:
            # 不做启发式误报，仅提示风格
            pass

    return results


# ============================================================
# 非 Python 正则回退（保留原有能力）
# ============================================================

SMELLS = [
    ("long_param", r"(?:def|function|func|public|private)\s+\w+\s*\(([^)]+)\)",
     lambda m: m and len([p for p in m.group(1).split(",") if p.strip()]) > 5,
     "参数过多 -> 用对象/struct 封装"),
    ("switch_statement", r"switch\s*\(|if\s+.*==.*else\s+if\s+.*==.*else\s+if",
     lambda m: True, "类型判断过多 -> 考虑用多态/策略模式"),
    ("dead_code", r"//\s*TODO.*\d{4}|//\s*FIXME.*\d{4}",
     lambda m: True, "过期 TODO/FIXME -> 清理或跟进"),
    ("magic_number", r"[^a-zA-Z\d](\d{2,})[^a-zA-Z\d]",
     lambda m: m and not m.group(1).startswith(("200", "201", "400", "401", "403", "404", "500")),
     "魔法数字 -> 提取为命名常量"),
    ("feature_envy", r"(\w+)\.\w+\.\w+\.\w+",
     lambda m: True, "过度链式调用 -> 违反迪米特法则"),
    ("inappropriate_intimacy", r"import\s+\w+\.\*|from\s+\w+\s+import\s+\*",
     lambda m: True, "通配符导入 -> 明确导入所需"),
    ("bad_name", r"\b(a|b|c|d|e|foo|bar|baz|x|y|z|tmp|temp|var|val)\b",
     lambda m: m and len(m.group(1)) <= 2,
     "单字母/无意义变量名 -> 用描述性名称"),
]


def analyze_file(filepath):
    """坏味道检测。Python 用 AST，其他语言用正则。返回 [(lineno|None, name, advice)]"""
    ext = Path(filepath).suffix.lower()
    try:
        content = Path(filepath).read_text(encoding="utf-8", errors="ignore")
    except Exception:
        return []
    lines = content.split("\n")
    results = []

    if ext in PY_EXTS:
        for lineno, name, advice in smell_ast(filepath, content):
            results.append((lineno, name, advice))
    else:
        for smell_name, pattern, condition, advice in SMELLS:
            if not pattern:
                continue
            for i, line in enumerate(lines, 1):
                m = re.search(pattern, line)
                if m and condition(m):
                    results.append((i, smell_name, advice))
                    if smell_name in ("switch_statement", "feature_envy", "inappropriate_intimacy"):
                        break  # one per file is enough

    return results


def main():
    parser = argparse.ArgumentParser(description="Code Smell Detector")
    parser.add_argument("--file")
    parser.add_argument("--dir", default=".")
    parser.add_argument("--format", choices=["text", "json"], default="text",
                        help="输出格式（json 供 CI 集成）")
    args = parser.parse_args()

    exts = {".py", ".js", ".ts", ".tsx", ".jsx", ".java", ".go", ".c", ".cpp", ".rs", ".rb"}
    ignore = {"node_modules", ".git", "dist", "build", "__pycache__", ".next", ".devflow"}

    all_results = []  # [(filepath, lineno, name, advice)]
    targets = [args.file] if args.file else []

    if not args.file:
        for root, dirs, files in os.walk(args.dir):
            dirs[:] = [d for d in dirs if d not in ignore]
            for f in files:
                if Path(f).suffix in exts:
                    targets.append(os.path.join(root, f))

    for t in targets:
        for lineno, name, advice in analyze_file(t):
            all_results.append((t, lineno, name, advice))

    if args.format == "json":
        issues = [
            {
                "file": fp,
                "line": lineno if lineno else None,
                "smell": name,
                "advice": advice,
            }
            for fp, lineno, name, advice in all_results
        ]
        import json
        print(json.dumps({"total": len(issues), "issues": issues},
                         ensure_ascii=False, indent=2))
    elif all_results:
        print(f"发现 {len(all_results)} 个代码坏味道:\n")
        for fp, lineno, name, advice in all_results:
            loc = f"{fp}:{lineno}" if lineno else fp
            print(f"[{name}] {loc} - {advice}")
    else:
        print("未发现明显坏味道 [OK]")


if __name__ == "__main__":
    main()
