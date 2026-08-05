#!/usr/bin/env python3
"""
DevFlow Fullstack - Code Review & Analysis

Python 文件使用 AST 分析（真实语法结构，误报更低）；其他语言回退到正则模式。

Usage: python review.py [--mode scan|readability|security|deadcode|duplication|all] [--file FILE | --dir DIR]
"""

import argparse
import ast
import hashlib
import json
import os
import re
import sys
from collections import defaultdict
from pathlib import Path

SEVERITY = {"L1": "[!!]致命", "L2": "[!]严重", "L3": "[*]警告", "L4": "[i]提示"}

PY_EXTS = {".py", ".pyw"}

# ============================================================
# 非 Python 语言的正则回退模式（保留原有能力）
# ============================================================

SECURITY_PATTERNS = [
    (r"execute\s*\(.*\\+", "L4", "SQL拼接 -> 应使用参数化查询"),
    (r"os\.system\(", "L4", "os.system() 存在命令注入风险 -> 改用 subprocess.run(shell=False)"),
    (r"eval\(", "L4", "eval() 危险用法 -> 改用 ast.literal_eval 或避免使用"),
    (r"innerHTML\s*=", "L4", "innerHTML 存在 XSS 风险 -> 改用 textContent 或 DOMPurify"),
    (r"dangerouslySetInnerHTML", "L4", "React dangerouslySetInnerHTML -> 建议使用 DOMPurify 净化"),
    (r"\.md5\(|\.sha1\(", "L4", "弱哈希算法 -> 改用 SHA256/bcrypt"),
    (r"password\s*=\s*[\x27\x22][^\x27\x22]+[\x27\x22]", "L4", "硬编码密码 -> 应使用环境变量"),
    (r"os\.popen\(|subprocess\.call\(.*shell\s*=\s*True", "L4", "命令执行存在注入风险 -> 改用 subprocess.run(shell=False)"),
    (r"\.execute\([^)]*f[\x27\x22]|\.execute\([^)]*%", "L4", "SQL注入: f-string/字符串拼接 -> 应使用参数化查询"),
    (r"xml\.etree|defusedxml|xml\.dom\.minidom", "L4", "XML 解析存在风险 -> 使用 defusedxml 防止 XXE"),
    (r"pickle\.loads?\(|yaml\.load\(", "L4", "反序列化风险 -> 使用 yaml.safe_load() / 避免 pickle"),
    (r"assert\s+.*password|assert\s+.*token", "L4", "assert 不能用于安全校验 -> 使用显式检查替代 assert"),
]

LOGIC_PATTERNS = [
    (r"except\s*:\s*pass", "L2", "空异常处理 -> 应至少记录日志"),
    (r"if\s+\w+\s*==\s*None:\s*\n\s*\w+\s*=\s*\[\]", "L2", "易出错写法 -> 使用 None 判断"),
    (r"==\s*True\b|==\s*False\b", "L2", "与 True/False 比较 -> 直接 if x / if not x"),
    (r"is\s+not\s+.*\s*==|is\s+.*\s*!=", "L2", "混淆 is 与 == -> is 用于对象身份比较"),
]

PERF_PATTERNS = [
    (r"for\s+.*\n\s*for\s+.*\n\s*.*\.find|\.filter|\.query", "L3", "循环内查询 -> 存在 N+1 问题"),
    (r"\.forEach.*\.query|\.map.*\.query", "L3", "循环内查询 -> 使用 JOIN/batch 批量处理"),
    (r"console\.log\(", "L3", "生产环境 console.log -> 应移除或降级为日志库"),
    (r"JSON\.parse\(JSON\.stringify", "L3", "深拷贝 -> 使用 structuredClone() 或 lodash.cloneDeep"),
    (r"\.concat\(", "L3", "字符串拼接 -> 使用 StringBuilder/join"),
    (r"\.readlines\(\)", "L3", "readlines() 一次性读入大文件 -> 逐行读取"),
    (r"sleep\(\d+\)", "L3", "硬编码 sleep -> 使用条件等待/超时机制"),
    (r"\+\s*=\s*[\x27\x22].*for\s+\w+\s+in", "L3", "循环内字符串拼接 -> 使用 join() 或 StringBuilder"),
    (r"import\s+\*", "L3", "通配符导入 -> 应改为按需导入"),
]


def is_pattern_definition(line):
    """跳过定义安全/性能模式的代码行（避免误报，仅正则回退用）"""
    return bool(re.search(r"SECURITY_PATTERNS|PERF_PATTERNS|r'|\"\"\"", line))


# ============================================================
# Python AST 分析
# ============================================================

PASSWORD_NAMES = {"password", "passwd", "pwd", "api_key", "apikey", "secret", "token"}
SQL_METHODS = {"execute", "executemany", "raw", "query"}
SUBPROCESS_METHODS = {"run", "call", "popen", "check_output", "check_call", "check_call"}
N1_ATTRS = {"query", "find", "filter", "fetchall", "fetchone", "execute", "executemany"}


def _safe_parse(content):
    try:
        return ast.parse(content)
    except SyntaxError:
        return None


def _call_names(node):
    """提取 ast.Call 的可读调用名，如 'os.system' / 'subprocess.run'"""
    func = node.func
    if isinstance(func, ast.Name):
        return [func.id]
    if isinstance(func, ast.Attribute):
        parts = []
        cur = func
        while isinstance(cur, ast.Attribute):
            parts.append(cur.attr)
            cur = cur.value
        if isinstance(cur, ast.Name):
            parts.append(cur.id)
        elif isinstance(cur, ast.Constant) and isinstance(cur.value, str):
            parts.append(cur.value)
        return [".".join(reversed(parts))]
    return []


def security_issues_py(tree):
    """Python AST 安全检测，返回 [(lineno, level, msg)]"""
    issues = []

    def add(lineno, level, msg):
        issues.append((lineno, level, msg))

    for node in ast.walk(tree):
        if isinstance(node, ast.Call):
            names = _call_names(node)

            # eval / exec / compile
            if any(n in ("eval", "exec") for n in names):
                add(node.lineno, "L4", "eval/exec 危险用法 -> 改用 ast.literal_eval 或避免使用")

            # os.system / os.popen
            if any(n in ("os.system", "os.popen", "os.spawn", "os.startfile") for n in names):
                add(node.lineno, "L4", "命令执行存在注入风险 -> 改用 subprocess.run(shell=False)")

            # subprocess with shell=True
            if any(n.startswith("subprocess.") and n.split(".")[1].lower() in SUBPROCESS_METHODS
                   for n in names):
                for kw in node.keywords:
                    if kw.arg == "shell" and isinstance(kw.value, ast.Constant) and kw.value.value is True:
                        add(node.lineno, "L4", "subprocess shell=True 存在命令注入风险 -> 使用参数数组")

            # 动态命令拼接: subprocess.run("..." % var / f"...")
            if any(n.startswith("subprocess.") and n.split(".")[1].lower() in SUBPROCESS_METHODS
                   for n in names) and node.args:
                arg = node.args[0]
                if isinstance(arg, ast.JoinedStr) or \
                   (isinstance(arg, ast.BinOp) and isinstance(arg.op, ast.Mod)):
                    add(node.lineno, "L4", "命令字符串拼接 -> 应传参数数组避免注入")

            # SQL 拼接
            if any(n.split(".")[-1] in SQL_METHODS for n in names) and node.args:
                arg = node.args[0]
                if isinstance(arg, ast.JoinedStr) or \
                   (isinstance(arg, ast.BinOp) and isinstance(arg.op, ast.Mod)) or \
                   (isinstance(arg, ast.Call) and isinstance(arg.func, ast.Attribute)
                        and arg.func.attr == "format"):
                    add(node.lineno, "L4", "SQL拼接 -> 应使用参数化查询")

            # pickle / yaml 反序列化
            if any(n == "pickle.load" or n == "pickle.loads" for n in names):
                add(node.lineno, "L4", "pickle 反序列化风险 -> 避免使用不可信数据")
            if any(n == "yaml.load" for n in names) and \
               not any(kw.arg == "Loader" and isinstance(kw.value, ast.Name)
                       and kw.value.id == "SafeLoader" for kw in node.keywords):
                add(node.lineno, "L4", "yaml.load 反序列化风险 -> 使用 yaml.safe_load()")

            # 弱哈希
            if any(n in ("hashlib.md5", "hashlib.sha1", "md5", "sha1") for n in names):
                add(node.lineno, "L4", "弱哈希算法 -> 改用 SHA256/bcrypt")

        # 硬编码密码 / 密钥
        if isinstance(node, ast.Assign):
            for t in node.targets:
                if isinstance(t, ast.Name) and t.id.lower() in PASSWORD_NAMES:
                    if isinstance(node.value, ast.Constant) and isinstance(node.value.value, str) \
                       and len(node.value.value) > 0:
                        add(node.lineno, "L4", "硬编码密码/密钥 -> 应使用环境变量")

        # assert 用于安全校验
        if isinstance(node, ast.Assert):
            names_in_test = [n.id for n in ast.walk(node.test) if isinstance(n, ast.Name)]
            if any(n in PASSWORD_NAMES for n in names_in_test):
                add(node.lineno, "L4", "assert 不能用于安全校验 -> 使用显式检查替代 assert")

    return issues


def logic_issues_py(tree):
    """Python AST 逻辑检测"""
    issues = []

    def add(lineno, level, msg):
        issues.append((lineno, level, msg))

    for node in ast.walk(tree):
        # 空 except
        if isinstance(node, ast.ExceptHandler):
            body = [s for s in node.body if not isinstance(s, ast.Pass)]
            if not body:
                add(node.lineno, "L2", "空异常处理 -> 应至少记录日志")

        # 与 True/False 比较
        if isinstance(node, ast.Compare) and len(node.ops) == 1 and len(node.comparators) == 1:
            if isinstance(node.ops[0], (ast.Eq, ast.NotEq)):
                comp = node.comparators[0]
                if isinstance(comp, ast.Constant) and isinstance(comp.value, bool):
                    add(node.lineno, "L2", "与 True/False 比较 -> 直接 if x / if not x")

        # 宽泛 except（except Exception 但不处理）
        if isinstance(node, ast.ExceptHandler):
            if node.type is None:
                add(node.lineno, "L2", "裸 except: -> 应指定具体异常类型")

    return issues


def perf_issues_py(tree):
    """Python AST 性能检测"""
    issues = []
    seen = set()

    def add(lineno, level, msg):
        key = (lineno, msg)
        if key not in seen:
            seen.add(key)
            issues.append((lineno, level, msg))

    for node in ast.walk(tree):
        # import *
        if isinstance(node, ast.ImportFrom) and node.names and any(n.name == "*" for n in node.names):
            add(node.lineno, "L3", "通配符导入 -> 应改为按需导入")

        # 循环内查询 (N+1)
        if isinstance(node, (ast.For, ast.While, ast.AsyncFor)):
            for sub in ast.walk(node):
                if isinstance(sub, ast.Call) and isinstance(sub.func, ast.Attribute):
                    if sub.func.attr in N1_ATTRS:
                        add(sub.lineno, "L3", "循环内查询 -> 存在 N+1 问题，使用 JOIN/batch 批量处理")

        # 循环内字符串拼接
        if isinstance(node, (ast.For, ast.While)):
            for sub in ast.walk(node):
                if isinstance(sub, ast.AugAssign) and isinstance(sub.op, ast.Add):
                    if isinstance(sub.value, ast.JoinedStr) or \
                       (isinstance(sub.value, ast.Constant) and isinstance(sub.value.value, str)):
                        add(sub.lineno, "L3", "循环内字符串拼接 -> 使用 join() 或列表收集")

        # readlines 一次性读入
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute) \
           and node.func.attr == "readlines":
            add(node.lineno, "L3", "readlines() 一次性读入大文件 -> 逐行读取")

        # 硬编码 sleep
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Name) \
           and node.func.id == "sleep":
            if node.args and isinstance(node.args[0], ast.Constant) \
               and isinstance(node.args[0].value, (int, float)):
                add(node.lineno, "L3", "硬编码 sleep -> 使用条件等待/超时机制")

    return issues


def cyclomatic_complexity(node):
    """计算子树的圈复杂度"""
    n = 1
    for sub in ast.walk(node):
        if isinstance(sub, (ast.If, ast.For, ast.While, ast.ExceptHandler,
                            ast.With, ast.Assert, ast.AsyncFor, ast.AsyncWith,
                            ast.Match)):
            n += 1
        elif isinstance(sub, ast.BoolOp):
            n += len(sub.values) - 1
    return n


def complexity_issues_py(tree):
    """对每个函数计算圈复杂度，过高时提示"""
    issues = []
    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            cc = cyclomatic_complexity(node)
            if cc > 15:
                issues.append((node.lineno, "L3",
                               f"函数 `{node.name}` 圈复杂度 {cc} -> 建议拆分（阈值 15）"))
    return issues


def unused_imports_py(tree):
    """检测未使用的导入，返回 [(lineno, name)]"""
    imported = {}
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for a in node.names:
                imported[a.asname or a.name.split(".")[0]] = node.lineno
        elif isinstance(node, ast.ImportFrom):
            for a in node.names:
                if a.name == "*":
                    continue
                imported[a.asname or a.name] = node.lineno

    used = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Name):
            used.add(node.id)
        elif isinstance(node, ast.Attribute):
            cur = node
            while isinstance(cur, ast.Attribute):
                cur = cur.value
            if isinstance(cur, ast.Name):
                used.add(cur.id)

    return [(lineno, name) for name, lineno in imported.items() if name not in used]


def _is_docstring(stmt):
    """判断语句是否为 docstring"""
    return (isinstance(stmt, ast.Expr)
            and isinstance(stmt.value, ast.Constant)
            and isinstance(stmt.value.value, str))


def _real_body_statements(body):
    """去掉 docstring 后剩下的实际语句（pass 也算）"""
    if body and _is_docstring(body[0]):
        return body[1:]
    return body


def empty_blocks_py(tree):
    """空 except / 空函数 / 空类，返回 [(lineno, kind, name)]"""
    out = []
    for node in ast.walk(tree):
        if isinstance(node, ast.ExceptHandler):
            if not [s for s in node.body if not isinstance(s, ast.Pass)]:
                out.append((node.lineno, "except", ""))
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            # 去掉 docstring 后无实际语句（仅 pass 或空）才算空函数
            real = _real_body_statements(node.body)
            if not real or all(isinstance(s, ast.Pass) for s in real):
                out.append((node.lineno, "function", node.name))
        if isinstance(node, ast.ClassDef):
            real = _real_body_statements(node.body)
            if not real or all(isinstance(s, ast.Pass) for s in real):
                out.append((node.lineno, "class", node.name))
    return out


# ============================================================
# 文件级扫描
# ============================================================

def scan_file(filepath):
    """对单个文件进行多层级扫描。Python 用 AST，其他语言用正则。"""
    ext = Path(filepath).suffix.lower()
    try:
        content = Path(filepath).read_text(encoding="utf-8", errors="ignore")
    except Exception as e:
        return [f"[ERR] {filepath}: {e}"]

    results = []
    lines = content.split("\n")

    if ext in PY_EXTS:
        tree = _safe_parse(content)
        if tree is None:
            # 语法错误：报告第一个 SyntaxError
            try:
                ast.parse(content)
            except SyntaxError as e:
                results.append(f"[L1] {filepath}:{e.lineno or 1} - 语法错误: {e.msg}")
            return results

        for lineno, level, msg in (security_issues_py(tree) + logic_issues_py(tree)
                                   + perf_issues_py(tree) + complexity_issues_py(tree)):
            results.append(f"[{level}] {filepath}:{lineno} - {msg}")
    else:
        for i, line in enumerate(lines, 1):
            for pattern, level, msg in SECURITY_PATTERNS + LOGIC_PATTERNS + PERF_PATTERNS:
                if re.search(pattern, line, re.IGNORECASE) \
                   and not re.search(r"// devflow-ignore|^\s*(#|//|/\*)", line) \
                   and not is_pattern_definition(line):
                    results.append(f"[{level}] {filepath}:{i} - {msg}")

    return results


def readability_score(filepath):
    """对代码可读性进行 1-10 分评分"""
    try:
        content = Path(filepath).read_text(encoding="utf-8", errors="ignore")
    except Exception as e:
        return {"file": filepath, "score": 0, "issues": [str(e)]}

    lines = content.split("\n")
    total_lines = len(lines)
    if total_lines == 0:
        return {"file": filepath, "score": 0, "issues": ["Empty file"]}

    ext = Path(filepath).suffix.lower()
    non_empty = [l for l in lines if l.strip() and not l.strip().startswith("//")
                 and not l.strip().startswith("#")]
    comment_lines = len([l for l in lines if l.strip().startswith(("//", "#", "/*", "*"))])

    long_funcs = []
    max_nesting = 0

    if ext in PY_EXTS:
        tree = _safe_parse(content)
        if tree is not None:
            # 用 AST 统计真实函数长度
            for node in ast.walk(tree):
                if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                    flen = (node.end_lineno or node.lineno) - node.lineno + 1
                    if flen > 30:
                        long_funcs.append(f"{node.name}({flen}行)")
            # 真实嵌套深度
            max_nesting = _max_nesting(tree)
        else:
            max_nesting = _regex_nesting(lines)
    else:
        max_nesting = _regex_nesting(lines)
        current_func = None
        func_lines = 0
        for line in lines:
            stripped = line.strip()
            if re.match(r"(def |function |func |public |private |protected )", stripped):
                if current_func and func_lines > 30:
                    long_funcs.append(f"{current_func}({func_lines}行)")
                current_func = stripped[:40]
                func_lines = 0
            if current_func:
                func_lines += 1

    comment_ratio = comment_lines / total_lines if total_lines > 0 else 0
    issues = []

    score = 10
    if comment_ratio < 0.05:
        issues.append(f"注释率仅 {comment_ratio:.1%} -> 建议 ≥10%")
        score -= 2
    if long_funcs:
        issues.append(f"函数过长: {', '.join(long_funcs[:3])}")
        score -= len(long_funcs) * 0.5
    if max_nesting > 3:
        issues.append(f"嵌套深度 {max_nesting} -> 建议 ≤3")
        score -= (max_nesting - 3) * 0.5
    if any(len(l) > 120 for l in non_empty):
        issues.append("存在超长行 (>120字符)")
        score -= 1

    return {
        "file": filepath,
        "score": max(1, round(score, 1)),
        "lines": total_lines,
        "comment_ratio": f"{comment_ratio:.1%}",
        "long_functions": len(long_funcs),
        "max_nesting": max_nesting,
        "issues": issues[:5]
    }


def _max_nesting(tree):
    """AST 递归求最大嵌套深度"""
    max_depth = [0]

    def walk(node, depth):
        max_depth[0] = max(max_depth[0], depth)
        for child in ast.iter_child_nodes(node):
            walk(child, depth + 1)

    walk(tree, 0)
    return max_depth[0]


def _regex_nesting(lines):
    """正则回退的嵌套深度估计"""
    nesting = 0
    max_nesting = 0
    for line in lines:
        stripped = line.strip()
        for ch in stripped:
            if ch in "{(":
                nesting += 1
            elif ch in "})":
                nesting = max(0, nesting - 1)
        max_nesting = max(max_nesting, nesting)
    return max_nesting


def find_dead_code(filepath):
    """查找潜在的死代码"""
    try:
        content = Path(filepath).read_text(encoding="utf-8", errors="ignore")
    except Exception:
        return []
    lines = content.split("\n")
    results = []
    ext = Path(filepath).suffix.lower()

    if ext in PY_EXTS:
        tree = _safe_parse(content)
        if tree is not None:
            for lineno, name in unused_imports_py(tree):
                results.append(f"{filepath}:{lineno} - 未使用的导入 `{name}`")
            for lineno, kind, name in empty_blocks_py(tree):
                if kind == "except":
                    results.append(f"{filepath}:{lineno} - 空 catch/except 块 -> 应至少记录日志")
                else:
                    results.append(f"{filepath}:{lineno} - 空{kind} `{name}` -> 应实现或删除")
    else:
        for i, line in enumerate(lines, 1):
            if re.search(r"catch\s*\(.*\)\s*\{\s*\}", line):
                results.append(f"{filepath}:{i} - 空 catch 块 -> 应至少记录日志")

    # TODO/FIXME 标记（所有语言）
    for i, line in enumerate(lines, 1):
        m = re.search(r"(?:#|//)\s*(TODO|FIXME|XXX|HACK)\b", line)
        if m:
            results.append(f"{filepath}:{i} - 遗留 {m.group(1)} 标记")

    return results


def find_duplications(dirpath):
    """查找跨文件的重复代码块"""
    exts = {".py", ".js", ".ts", ".tsx", ".jsx", ".java", ".go", ".c", ".cpp", ".rs", ".rb", ".php"}
    ignore = {"node_modules", ".git", "__pycache__", "dist", "build", ".next", "target", "vendor"}
    block_map = defaultdict(list)

    for root, dirs, files in os.walk(dirpath):
        dirs[:] = [d for d in dirs if d not in ignore]
        for f in files:
            if Path(f).suffix not in exts:
                continue
            fp = os.path.join(root, f)
            try:
                lines = Path(fp).read_text(encoding="utf-8", errors="ignore").split("\n")
            except Exception:
                continue
            for i in range(len(lines) - 4):
                block = "\n".join(l.strip() for l in lines[i:i+5] if l.strip())
                if len(block) < 30 or not block:
                    continue
                h = hashlib.md5(block.encode()).hexdigest()
                block_map[h].append(f"{fp}:{i+1}")

    results = []
    for h, locations in block_map.items():
        if len(locations) >= 2:
            results.append(f"重复代码块 ({len(locations)} 处): " + ", ".join(locations[:3]))
    return results


def scan_dir(dirpath, mode="scan"):
    """扫描整个目录"""
    all_results = []
    exts = {".py", ".js", ".ts", ".tsx", ".jsx", ".java", ".go", ".c", ".cpp", ".rs", ".rb", ".php"}
    ignore = {"node_modules", ".git", "__pycache__", "dist", "build", ".next", "target", "vendor"}

    for root, dirs, files in os.walk(dirpath):
        dirs[:] = [d for d in dirs if d not in ignore]
        for f in files:
            if Path(f).suffix in exts:
                fp = os.path.join(root, f)
                if mode == "scan":
                    all_results.extend(scan_file(fp))
                elif mode == "readability":
                    all_results.append(readability_score(fp))
                elif mode == "deadcode":
                    all_results.extend(find_dead_code(fp))
                elif mode == "security":
                    for r in scan_file(fp):
                        if "L4" in r or "L3" in r:
                            all_results.append(r)

    return all_results


def append_toolchain_results(results, target, mode):
    """附加成熟工具链（bandit/ruff）的结果。target 为文件或目录。"""
    try:
        import toolchain
    except ImportError:
        return

    if mode not in ("scan", "security"):
        return

    # bandit：对目录做安全扫描
    ok, out = toolchain.run_bandit(target)
    if ok and out and "未安装" not in out:
        results.append("\n--- Bandit (第三方工具) ---")
        # 提取关键行，避免过长
        for line in out.split("\n"):
            if any(tag in line for tag in ["Issue:", "Severity:", "CWE", ">> Issue", "[medium]", "[high]"]):
                results.append("  " + line.strip())

    # ruff：仅对目录 lint
    if mode == "scan":
        ok2, out2 = toolchain.run_ruff(target)
        if ok2 and out2 and "未安装" not in out2:
            results.append("\n--- Ruff (第三方工具) ---")
            lines2 = out2.split("\n")
            for line in lines2[:20]:
                if line.strip():
                    results.append("  " + line.strip())


def main():
    parser = argparse.ArgumentParser(description="DevFlow Code Review")
    parser.add_argument("--mode", default="scan", choices=["scan", "readability", "security", "deadcode", "duplication", "all"])
    parser.add_argument("--file")
    parser.add_argument("--dir", default=".")
    parser.add_argument("--format", choices=["text", "json"], default="text")
    parser.add_argument("--with-tools", action="store_true",
                        help="附加第三方工具结果（bandit/ruff，若已安装）")
    args = parser.parse_args()

    target = args.file if args.file else args.dir

    if args.mode == "scan":
        results = scan_file(target) if args.file else scan_dir(target, "scan")
        if args.with_tools:
            append_toolchain_results(results, target, "scan")
        if args.format == "json":
            print(json.dumps({"total": len(results), "issues": results}, ensure_ascii=False, indent=2))
        else:
            for r in results:
                print(r)
            print(f"\n共 {len(results)} 条发现")

    elif args.mode == "security":
        results = scan_file(target) if args.file else scan_dir(target, "security")
        if args.with_tools:
            append_toolchain_results(results, target, "security")
        if args.format == "json":
            print(json.dumps({"total": len(results), "issues": results}, ensure_ascii=False, indent=2))
        else:
            for r in results:
                print(r)
            print(f"\n共 {len(results)} 条安全发现")

    elif args.mode == "readability":
        results = [readability_score(target)] if args.file else scan_dir(target, "readability")
        if args.format == "json":
            print(json.dumps({"total": len(results), "files": results}, ensure_ascii=False, indent=2))
        else:
            for r in results:
                print(f"{r['file']}: 评分 {r['score']}/10 | {r['lines']}行 | 注释率{r.get('comment_ratio','N/A')} | 嵌套{r.get('max_nesting','?')}层")
                for i in r.get("issues", []):
                    print(f"  -> {i}")

    elif args.mode == "deadcode":
        results = find_dead_code(target) if args.file else scan_dir(target, "deadcode")
        if args.format == "json":
            print(json.dumps({"total": len(results), "issues": results}, ensure_ascii=False, indent=2))
        else:
            for r in results:
                print(r)

    elif args.mode == "duplication":
        results = find_duplications(target)
        if args.format == "json":
            print(json.dumps({"total": len(results), "issues": results}, ensure_ascii=False, indent=2))
        else:
            for r in results:
                print(r)
            print(f"\n共 {len(results)} 处重复")

    elif args.mode == "all":
        print("=== Bug 扫描 ===")
        scan_results = scan_dir(target, "scan")
        for r in scan_results:
            print(r)
        print(f"\n=== 可读性评估 ===")
        read_results = scan_dir(target, "readability")
        for r in read_results:
            print(f"  {r['file']}: {r['score']}/10")
        print(f"\n=== 死代码检测 ===")
        dead_results = scan_dir(target, "deadcode")
        for r in dead_results:
            print(r)
        print(f"\n=== 重复代码检测 ===")
        dup_results = find_duplications(target)
        for r in dup_results[:20]:
            print(f"  {r}")


if __name__ == "__main__":
    main()
