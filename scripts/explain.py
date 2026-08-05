#!/usr/bin/env python3
"""
DevFlow - Code <-> Natural Language Translator (#30)
Usage:
  python explain.py --file foo.py              # code -> structural analysis
  python explain.py --file foo.py --line 42    # explain specific line
  python explain.py --file foo.py --llm        # code -> human language (requires LLM)

--llm 模式需要配置模型（见 model-manager.py）或设置 OPENAI_API_KEY/ANTHROPIC_API_KEY。
未配置时自动回退到结构分析。
"""

import argparse
import re
import sys
from pathlib import Path

# 确保可 import 同目录模块
sys.path.insert(0, str(Path(__file__).resolve().parent))

LANG_MAP = {".py": "Python", ".js": "JavaScript", ".ts": "TypeScript", ".tsx": "React+TS",
            ".jsx": "React", ".java": "Java", ".go": "Go", ".c": "C", ".cpp": "C++", ".rs": "Rust"}

def analyze_structure(filepath):
    """Extract code structure: imports, functions, classes, complexity hints"""
    content = Path(filepath).read_text(encoding="utf-8", errors="ignore")
    lines = content.split("\n")
    ext = Path(filepath).suffix
    lang = LANG_MAP.get(ext, "Unknown")

    result = [f"# 代码分析: {Path(filepath).name}", f"语言: {lang}", f"总行数: {len(lines)}", ""]

    # Functions
    funcs = []
    for i, line in enumerate(lines, 1):
        m = re.match(r"(?:def|function|func|public|private|protected|static|async)\s+(\w+)\s*\(([^)]*)\)", line.strip())
        if m:
            funcs.append({"line": i, "name": m.group(1), "params": m.group(2)})

    if funcs:
        result.append("## 函数列表")
        for f in funcs:
            params_str = f['params'].strip() if f['params'].strip() else "无参数"
            result.append(f"- **{f['name']}**(第{f['line']}行): 参数={params_str}")
    else:
        result.append("- 未检测到函数定义")

    # Imports
    imports = [l.strip() for l in lines if l.strip().startswith(("import ","from ","require(","use "))]
    if imports:
        result.append(f"\n## 依赖导入 ({len(imports)}个)")
        for imp in imports[:5]:
            result.append(f"- `{imp}`")

    # Complexity indicators
    loops = sum(1 for l in lines if re.search(r"\b(for|while)\s*\(", l))
    conditionals = sum(1 for l in lines if re.search(r"\bif\s+", l))
    try_blocks = sum(1 for l in lines if re.search(r"\btry\s*:", l))

    result.append(f"\n## 复杂度概览")
    result.append(f"- 循环: {loops} 个")
    result.append(f"- 条件分支: {conditionals} 个")
    result.append(f"- 异常处理: {try_blocks} 个")

    if loops > 5:
        result.append("  [!] 循环较多，检查是否有优化空间")
    if conditionals > 10:
        result.append("  [!] 条件分支较多，考虑策略模式或多态")

    return "\n".join(result)

def explain_line(filepath, line_num, context=3):
    """Explain what a specific line does"""
    content = Path(filepath).read_text(encoding="utf-8", errors="ignore")
    lines = content.split("\n")
    start = max(0, line_num - context - 1)
    end = min(len(lines), line_num + context)

    result = [f"# 行 {line_num} 上下文分析\n"]
    result.append("```")
    for i in range(start, end):
        marker = "-> " if i == line_num - 1 else "  "
        result.append(f"{marker}{i+1}: {lines[i]}")
    result.append("```")

    target = lines[line_num - 1].strip() if line_num <= len(lines) else ""
    if target:
        result.append(f"\n**代码**: `{target[:80]}`")
        # Pattern-based explanations
        if "=" in target and "==" not in target:
            result.append("- 这是一个**赋值**操作")
        if re.search(r"\bif\b", target):
            result.append("- 这是一个**条件判断**")
        if re.search(r"\bfor\b|\bwhile\b", target):
            result.append("- 这是一个**循环**")
        if re.search(r"\bdef\b|\bfunction\b", target):
            result.append("- 这是一个**函数定义**")
        if re.search(r"\breturn\b", target):
            result.append("- 这是函数的**返回**语句")
        if re.search(r"\btry\b", target):
            result.append("- 这是**异常处理**的开始")
        if re.search(r"\bprint\b|\bconsole\.log\b", target):
            result.append("- 这是**调试输出**")

    return "\n".join(result)

def llm_explain(filepath, line_num=None):
    """使用 LLM 做语义解释。未配置 LLM 时返回 None。"""
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

    lang = LANG_MAP.get(Path(filepath).suffix, "Unknown")
    if line_num:
        lines = content.split("\n")
        target = lines[line_num - 1].strip() if line_num <= len(lines) else ""
        prompt = (f"这是一个{lang}代码文件。请用通俗的语言解释第 {line_num} 行代码："
                  f"`{target}`\n\n完整代码片段：\n```\n{chr(10).join(lines[max(0,line_num-6):line_num+4])}\n```\n"
                  f"解释时说明：这行在做什么、为什么这样写、可能的风险。")
    else:
        prompt = (f"这是一个{lang}代码文件。请用通俗的语言解释它的整体逻辑、"
                  f"关键函数的作用、以及潜在的问题。请说人话，不堆术语。\n\n"
                  f"```{lang.lower()}\n{content[:8000]}\n```")
    try:
        return llm.chat(prompt, system="你是 DevFlow 的代码解释助手，善于用通俗语言解释代码。")
    except Exception as e:
        return f"[LLM 调用失败] {e}"


def main():
    parser = argparse.ArgumentParser(description="Code <-> Natural Language Translator")
    parser.add_argument("--file", required=True)
    parser.add_argument("--line", type=int, help="解释特定行")
    parser.add_argument("--llm", action="store_true",
                        help="使用 LLM 做语义解释（需配置模型；未配置自动回退）")
    args = parser.parse_args()

    if args.llm:
        result = llm_explain(args.file, args.line)
        if result:
            print(result)
            return
        # LLM 不可用，回退到结构分析并提示
        print(f"[提示] 未配置 LLM，回退到结构分析。"
              f"（配置方式：python model-manager.py --config --provider openai --api-key ...）\n")

    if args.line:
        print(explain_line(args.file, args.line))
    else:
        print(analyze_structure(args.file))


if __name__ == "__main__":
    main()
