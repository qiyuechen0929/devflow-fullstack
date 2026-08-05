#!/usr/bin/env python3
"""
DevFlow - Test Generator

使用 AST 解析 Python 函数签名（参数、默认值、类型标注），生成可编译、参数匹配的真实测试骨架。
其他语言回退到正则提取。

Usage:
  python testgen.py --file calculator.py --framework pytest
  python testgen.py --file UserService.java --framework junit
  python testgen.py --dir src/ --framework jest
"""

import argparse
import ast
import os
import re
import sys
from pathlib import Path

# 确保可 import 同目录模块（llm 等）
sys.path.insert(0, str(Path(__file__).resolve().parent))

PY_EXTS = {".py", ".pyw"}

# 常见类型 → 示例值
TYPE_SAMPLES = {
    "int": "42",
    "float": "3.14",
    "str": "'hello'",
    "bool": "True",
    "list": "[]",
    "dict": "{}",
    "set": "set()",
    "tuple": "()",
    "Any": "None",
    "Optional": "None",
    "Path": "Path('.')",
    "bytes": "b''",
}
# 默认值判断
_NONE_DEFAULTS = {None, ""}


def _type_sample(annotation_node):
    """从类型标注节点推断示例值"""
    if annotation_node is None:
        return None
    if isinstance(annotation_node, ast.Name):
        t = annotation_node.id
        return TYPE_SAMPLES.get(t)
    if isinstance(annotation_node, ast.Subscript):
        # Optional[int] / List[str] 等
        if isinstance(annotation_node.value, ast.Name):
            base = annotation_node.value.id
            if base == "Optional":
                return None
            if base in ("List", "Sequence", "Iterable", "tuple"):
                return "[]"
            if base in ("Dict", "Mapping"):
                return "{}"
            if base in ("Set",):
                return "set()"
            return TYPE_SAMPLES.get(base)
    return None


class _FuncInfo:
    __slots__ = ("name", "params", "defaults", "annotations", "is_method",
                 "lineno", "class_name")

    def __init__(self, name, params, defaults, annotations, is_method, lineno, class_name=None):
        self.name = name
        self.params = params          # [arg_name,...]（不含 self/cls）
        self.defaults = defaults      # {arg_name: repr}
        self.annotations = annotations  # {arg_name: sample_value or None}
        self.is_method = is_method
        self.lineno = lineno
        self.class_name = class_name


def extract_functions_py(content):
    """AST 提取 Python 函数签名"""
    try:
        tree = ast.parse(content)
    except SyntaxError:
        return []

    # 建一个 id→类名 的映射，找出每个函数是否在类体内
    funcs = []

    class _Collector(ast.NodeVisitor):
        def __init__(self):
            self.stack = []  # 每层是 class_name or None

        def _current_class(self):
            for c in reversed(self.stack):
                if c is not None:
                    return c
            return None

        def visit_ClassDef(self, node):
            self.stack.append(node.name)
            for stmt in node.body:
                if isinstance(stmt, (ast.FunctionDef, ast.AsyncFunctionDef)):
                    self.visit(stmt)
            # 不递归处理嵌套类/方法，直接遍历当前类体的顶层函数
            self.stack.pop()

        def visit_FunctionDef(self, node):
            cls = self._current_class()
            self._collect(node, cls)

        def visit_AsyncFunctionDef(self, node):
            cls = self._current_class()
            self._collect(node, cls)

        def _collect(self, node, cls):
            args = node.args
            pos_params = [a.arg for a in args.posonlyargs + args.args]
            kw_params = [a.arg for a in args.kwonlyargs]
            all_params = pos_params + kw_params

            defaults = {}
            pos_defaults = args.defaults
            n_pos = len(pos_params)
            n_def = len(pos_defaults)
            for i in range(n_def):
                d = pos_defaults[n_def - 1 - i]
                defaults[pos_params[n_pos - 1 - i]] = _const_repr(d)
            for a, d in zip(args.kwonlyargs, args.kw_defaults):
                if d is not None:
                    defaults[a.arg] = _const_repr(d)

            is_method = cls is not None
            filtered = []
            for i, p in enumerate(all_params):
                if i == 0 and p in ("self", "cls"):
                    continue
                filtered.append(p)

            annotations = {}
            for a in args.posonlyargs + args.args + args.kwonlyargs:
                if a.arg in ("self", "cls"):
                    continue
                if a.arg in defaults:
                    annotations[a.arg] = defaults[a.arg]
                else:
                    sample = _type_sample(a.annotation) if a.annotation else None
                    annotations[a.arg] = sample

            funcs.append(_FuncInfo(node.name, filtered, defaults, annotations,
                                   is_method, node.lineno, cls))

    _Collector().visit(tree)
    return funcs


def _const_repr(node):
    """把 AST 常量节点转成 repr 字符串"""
    if isinstance(node, ast.Constant):
        if node.value is None:
            return "None"
        if isinstance(node.value, str):
            return repr(node.value)
        if isinstance(node.value, bool):
            return "True" if node.value else "False"
        return repr(node.value)
    if isinstance(node, ast.Name):
        return node.id
    if isinstance(node, ast.List):
        return "[]"
    if isinstance(node, ast.Dict):
        return "{}"
    if isinstance(node, ast.Tuple):
        return "()"
    if isinstance(node, ast.UnaryOp) and isinstance(node.op, ast.USub):
        inner = _const_repr(node.operand)
        return f"-{inner}"
    return None


def extract_functions_regex(filepath):
    """正则回退提取函数（非 Python）"""
    try:
        content = Path(filepath).read_text(encoding="utf-8", errors="ignore")
    except Exception:
        return []
    funcs = []
    patterns = [
        (r"public\s+\w+\s+(\w+)\s*\(([^)]*)\)", "java"),
        (r"export\s+(?:async\s+)?function\s+(\w+)\s*\(([^)]*)\)", "ts"),
        (r"(?:const|let|var)\s+(\w+)\s*=\s*(?:async\s*)?\(([^)]*)\)\s*=>", "ts"),
    ]
    for pattern, lang in patterns:
        for m in re.finditer(pattern, content):
            name = m.group(1)
            if name.startswith("_"):
                continue
            params = [p.strip().split(" ")[-1].strip() for p in m.group(2).split(",") if p.strip()]
            funcs.append({"name": name, "params": params, "lang": lang})
    return funcs


def generate_tests(funcs, framework, module_name):
    if framework not in FRAMEWORKS:
        return f"不支持的框架: {framework}"

    config = FRAMEWORKS[framework]
    if framework == "pytest":
        module_import = f"from {module_name} import *"
    else:
        fnames = ", ".join(f["name"] for f in funcs[:3])
        module_import = f"import {{ {fnames} }} from './{module_name}'"

    result = [config["imports"].format(module_import=module_import)]

    for func in funcs[:5]:
        if framework == "pytest":
            block = _gen_pytest(func)
        elif framework == "junit":
            block = _gen_junit(func)
        else:
            block = _gen_jest(func)
        result.append(block)

    if framework == "jest":
        result.append("})")

    return "\n".join(result)


def _sample_args(func):
    """生成参数示例值，返回 (normal_args_str, edge_args_str)"""
    params = func.params
    if not params:
        return "", ""

    normal = []
    edge = []
    for p in params:
        sample = func.annotations.get(p)
        if sample is not None:
            normal.append(str(sample))
            edge.append("None")
        else:
            normal.append("None")
            edge.append("None")

    return ", ".join(normal), ", ".join(edge)


def _call_line(func, args_str):
    """构造调用行。方法是实例方法时通过类实例调用。"""
    if func.is_method and func.class_name:
        # 跳过 __init__ 单独生成；其余方法用 Class().method(...)
        if func.name == "__init__":
            return f"{func.class_name}({args_str})"
        return f"{func.class_name}().{func.name}({args_str})"
    if func.name == "__init__":
        return f"{func.class_name}({args_str})"
    return f"{func.name}({args_str})"


def _gen_pytest(func):
    name = func.name
    normal, edge = _sample_args(func)
    call_normal = _call_line(func, normal)
    call_edge = _call_line(func, edge)

    lines = [f"def test_{name}_normal():",
             "    \"\"\"正常路径\"\"\"",
             f"    result = {call_normal}",
             "    assert result is not None",
             "",
             "",
             f"def test_{name}_edge_cases():",
             "    \"\"\"边界场景：空值/异常输入\"\"\"",
             f"    try:",
             f"        {call_edge}",
             "    except (ValueError, TypeError) as e:",
             "        # 空值可能抛类型错误，符合预期",
             "        assert isinstance(e, (ValueError, TypeError))",
             "",
             "",
             f"def test_{name}_error_handling():",
             "    \"\"\"异常处理：极值输入\"\"\"",
             "    try:",
             f"        {call_normal}",
             "    except Exception:",
             "        pass",
             "",
             ""]
    return "\n".join(lines)


def _gen_junit(func):
    name = func.name
    cap = name[0].upper() + name[1:]
    normal, edge = _sample_args(func)
    call_normal = _call_line(func, normal)
    call_edge = _call_line(func, edge)
    return f"""@Test
void test{cap}_normal() {{
    // 正常路径
    var result = {call_normal};
    assertNotNull(result);
}}

@Test
void test{cap}_edgeCases() {{
    // 边界场景：空值
    assertThrows(Exception.class, () -> {call_edge});
}}
"""


def _gen_jest(func):
    name = func.name
    cap = name[0].upper() + name[1:]
    normal, edge = _sample_args(func)
    call_normal = _call_line(func, normal)
    call_edge = _call_line(func, edge)
    return f"""  describe('{cap}', () => {{
    it('should handle normal input', () => {{
      const result = {call_normal}
      expect(result).toBeDefined()
    }})

    it('should handle edge cases', () => {{
      expect(() => {call_edge}).toThrow()
    }})
  }})
"""


FRAMEWORKS = {
    "pytest": {"imports": "import pytest\nimport sys\nsys.path.insert(0, '.')\n\n{module_import}\n"},
    "junit": {"imports": 'import org.junit.jupiter.api.Test;\nimport static org.junit.jupiter.api.Assertions.*;\n\n{module_import}\n'},
    "jest": {"imports": "{module_import}\n"},
}


def llm_generate_tests(filepath, framework):
    """使用 LLM 生成真实语义测试。未配置 LLM 时返回 None。"""
    try:
        import llm
    except ImportError:
        return None
    if not llm.is_available():
        return None

    try:
        content = Path(filepath).read_text(encoding="utf-8", errors="ignore")
    except Exception:
        return None

    lang = "Python" if Path(filepath).suffix.lower() in PY_EXTS else Path(filepath).suffix.lstrip(".").upper()
    prompt = (
        f"这是 {lang} 代码文件。请为它生成 {framework} 框架的测试文件。\n"
        f"要求：\n"
        f"1. 覆盖正常路径、边界值、异常路径\n"
        f"2. 测试必须真实调用代码并断言具体结果（不要用 assert result is not None 这种占位）\n"
        f"3. 只输出测试代码，不要额外说明\n\n"
        f"```{lang.lower()}\n{content[:8000]}\n```"
    )
    try:
        result = llm.chat(prompt, system="你是 DevFlow 的测试生成助手，只输出可运行的测试代码。")
        # 清理代码块围栏
        lines = result.strip().split("\n")
        if lines and lines[0].strip().startswith("```"):
            lines = lines[1:]
        if lines and lines[-1].strip().startswith("```"):
            lines = lines[:-1]
        return "\n".join(lines).strip()
    except Exception as e:
        return f"[LLM 调用失败] {e}"


def main():
    parser = argparse.ArgumentParser(description="Test Generator")
    parser.add_argument("--file", required=True)
    parser.add_argument("--framework", default="pytest", choices=list(FRAMEWORKS.keys()))
    parser.add_argument("--output")
    parser.add_argument("--llm", action="store_true",
                        help="使用 LLM 生成真实语义测试（需配置模型；未配置自动回退到模板）")
    args = parser.parse_args()

    filepath = args.file
    ext = Path(filepath).suffix.lower()

    if args.llm:
        llm_tests = llm_generate_tests(filepath, args.framework)
        if llm_tests:
            if args.output:
                Path(args.output).write_text(llm_tests, encoding="utf-8")
                print(f"已生成测试文件 (LLM): {args.output}")
            else:
                print(llm_tests)
            return
        print(f"[提示] 未配置 LLM，回退到模板生成。"
              f"（配置方式：python model-manager.py --config --provider openai --api-key ...）\n")

    if ext in PY_EXTS:
        try:
            content = Path(filepath).read_text(encoding="utf-8", errors="ignore")
        except Exception as e:
            print(f"读取文件失败: {e}")
            return
        funcs = extract_functions_py(content)
    else:
        funcs = extract_functions_regex(filepath)

    if not funcs:
        print("未检测到可测试的函数")
        return

    module_name = Path(filepath).stem
    tests = generate_tests(funcs, args.framework, module_name)

    if args.output:
        Path(args.output).write_text(tests, encoding="utf-8")
        print(f"已生成测试文件: {args.output}")
    else:
        print(tests)


if __name__ == "__main__":
    main()
