#!/usr/bin/env python3
"""
DevFlow - Boundary Case Generator (#12)
Usage: python boundary.py --file foo.py --func calculate_total
"""

import argparse, re
from pathlib import Path

def infer_type(param_name):
    """Infer boundary values from parameter name"""
    name = param_name.lower()
    if any(k in name for k in ("id","count","num","size","index","age")):
        return "int", [-1, 0, 1, 100, 2**31-1, -2**31]
    if any(k in name for k in ("price","amount","rate","total","sum")):
        return "float", [0.0, -0.01, 0.01, 1e10, float("inf"), float("-inf")]
    if any(k in name for k in ("name","title","text","str","msg")):
        return "str", ["", "a", "a"*1000, "   ", "\\n\\t", None, "<script>"]
    if any(k in name for k in ("email","mail")):
        return "str", ["", "not-an-email", "a@b", "a"*100+"@x.com", None]
    if any(k in name for k in ("url","link","href")):
        return "str", ["", "not-a-url", "/relative", "https://"+("x"*1000), None]
    if any(k in name for k in ("list","array","items","data")):
        return "list", [[], None, [1]*10000, [None]]
    return "any", [None, 0, "", [], {}]

def extract_function(filepath, func_name):
    content = Path(filepath).read_text(encoding="utf-8", errors="ignore")
    pattern = rf"(?:def|function|public\s+\w+)\s+{func_name}\s*\(([^)]*)\)"
    m = re.search(pattern, content)
    if not m:
        return None
    params = [p.strip().split(":")[0].split("=")[0].strip() for p in m.group(1).split(",") if p.strip()]
    return [p for p in params if p not in ("self","cls","this")]

def generate_cases(func_name, params):
    if not params:
        return ["# 无参数函数 - 只需测试调用"]

    cases = []
    cases.append(f"# {func_name} - 边界测试用例")
    cases.append("")
    cases.append("## 正常路径")
    cases.append("| 输入 | 预期 |")
    cases.append("|------|------|")
    normal_args = ", ".join(p + "=valid_value" for p in params)
    cases.append(f"| {func_name}({normal_args}) | 正常返回 |")
    cases.append("")

    cases.append("## 边界值")
    cases.append("| 参数 | 测试值 | 风险 |")
    cases.append("|------|--------|------|")
    for p in params:
        ptype, values = infer_type(p)
        for v in values[:4]:
            risk = ""
            if v is None: risk = "空指针"
            elif v == "": risk = "空字符串"
            elif isinstance(v, int) and v < 0: risk = "负数"
            elif isinstance(v, (int, float)) and v > 100000: risk = "溢出"
            cases.append(f"| `{p}` | `{repr(v)}` ({ptype}) | {risk} |")

    cases.append("")
    cases.append("## 特殊场景")
    cases.append("- 并发调用: 同时 10 个请求")
    cases.append("- 重复调用: 连续 1000 次")
    cases.append("- 注入攻击: SQL/HTML/JS 特殊字符")

    return "\n".join(cases)

def main():
    parser = argparse.ArgumentParser(description="Boundary Case Generator")
    parser.add_argument("--file", required=True)
    parser.add_argument("--func", required=True, help="函数名")
    args = parser.parse_args()

    params = extract_function(args.file, args.func)
    if params is None:
        print(f"未找到函数: {args.func}")
        return

    print(f"函数: {args.func}({', '.join(params)})")
    print()
    print(generate_cases(args.func, params))

if __name__ == "__main__":
    main()
