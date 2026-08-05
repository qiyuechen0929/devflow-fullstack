#!/usr/bin/env python3
"""
DevFlow - Claude Code PostToolUse Hook
保存文件后自动执行 DevFlow 快速安全审查。

配置在 .claude/settings.json 的 hooks 中，关联 PostToolUse 事件。
Claude Code 会通过 stdin 传入工具调用 JSON。
"""
import json
import os
import subprocess
import sys

# 从 stdin 读取 Claude Code 的 hook 输入
def main():
    try:
        input_data = json.load(sys.stdin)
    except (json.JSONDecodeError, Exception):
        input_data = {}

    # 只对文件写入类工具生效
    tool_name = input_data.get("tool_name", "")
    if tool_name not in ("Write", "Edit", "MultiEdit"):
        return

    # 提取文件路径
    tool_input = input_data.get("tool_input", {})
    file_path = tool_input.get("file_path", tool_input.get("path", ""))

    if not file_path or not os.path.isfile(file_path):
        return

    # 只检查代码文件
    exts = (".py", ".js", ".ts", ".jsx", ".tsx", ".java", ".go", ".c", ".cpp", ".rs", ".rb")
    if not file_path.endswith(exts):
        return

    # 定位 DevFlow 脚本目录（相对于 hook 脚本）
    hook_dir = os.path.dirname(os.path.abspath(__file__))
    project_root = os.path.dirname(os.path.dirname(hook_dir))
    scripts_dir = os.path.join(project_root, "scripts")
    review_script = os.path.join(scripts_dir, "review.py")

    if not os.path.isfile(review_script):
        return

    # 运行安全审查
    try:
        result = subprocess.run(
            [sys.executable, review_script, "--mode", "security", "--file", file_path],
            capture_output=True, text=True, timeout=30,
            encoding="utf-8", errors="replace"
        )
        output = (result.stdout + result.stderr).strip()
        if output and ("[L4]" in output or "[L3]" in output):
            # 输出到 stderr 会显示在 Claude Code 里
            critical = output.count("[L4]")
            warning = output.count("[L3]")
            print(f"⚠️ DevFlow 审查: 高危 {critical} 处, 警告 {warning} 处")
            # 只显示前 5 行
            for line in output.split("\n")[:5]:
                print(f"  {line}")
    except Exception:
        pass


if __name__ == "__main__":
    main()
