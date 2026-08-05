#!/usr/bin/env python3
"""
DevFlow - 成熟工具链桥接层

自动检测环境中已安装的第三方静态分析工具（Bandit / Ruff / pytest），
已安装则优先调用成熟工具，未安装则回退到自研脚本。

用法（供其他脚本 import）：
    from toolchain import detect_tools, run_bandit, run_ruff, run_pytest, make_toolchain_report
"""

import json
import shutil
import subprocess
import sys
from pathlib import Path


def _py_module_available(module):
    try:
        __import__(module)
        return True
    except ImportError:
        return False


def _command_available(cmd):
    """判定命令是否可用：优先 python -m 方式（与运行方式一致）"""
    if _py_module_available(cmd):
        return True
    return shutil.which(cmd) is not None


def detect_tools():
    """检测可用的第三方工具，返回 {tool: available_bool}"""
    return {
        "bandit": _command_available("bandit"),
        "ruff": _command_available("ruff"),
        "pytest": _command_available("pytest"),
    }


def run_bandit(target_dir, verbose=False):
    """运行 Bandit 安全扫描，返回 (ok, output)"""
    if not _command_available("bandit"):
        return False, "bandit 未安装，跳过"
    cmd = [sys.executable, "-m", "bandit", "-r", str(target_dir), "-q", "-f", "txt"]
    try:
        r = subprocess.run(cmd, capture_output=True, text=True, timeout=120,
                           encoding="utf-8", errors="replace")
        return True, (r.stdout or r.stderr).strip()
    except subprocess.TimeoutExpired:
        return True, "bandit 超时（>120s）"
    except Exception as e:
        return True, f"bandit 执行失败: {e}"


def run_ruff(target_dir, verbose=False):
    """运行 Ruff lint，返回 (ok, output)"""
    if not _command_available("ruff"):
        return False, "ruff 未安装，跳过"
    cmd = [sys.executable, "-m", "ruff", "check", str(target_dir)]
    try:
        r = subprocess.run(cmd, capture_output=True, text=True, timeout=120,
                           encoding="utf-8", errors="replace")
        return True, (r.stdout or r.stderr).strip()
    except subprocess.TimeoutExpired:
        return True, "ruff 超时（>120s）"
    except Exception as e:
        return True, f"ruff 执行失败: {e}"


def run_pytest(target_dir, verbose=False):
    """运行 pytest 测试，返回 (ok, output)"""
    if not _command_available("pytest"):
        return False, "pytest 未安装，跳过"
    cmd = [sys.executable, "-m", "pytest", "-q", str(target_dir)]
    try:
        r = subprocess.run(cmd, capture_output=True, text=True, timeout=120,
                           encoding="utf-8", errors="replace")
        return True, (r.stdout or r.stderr).strip()
    except subprocess.TimeoutExpired:
        return True, "pytest 超时（>120s）"
    except Exception as e:
        return True, f"pytest 执行失败: {e}"


def make_toolchain_report(target_dir):
    """生成工具链检测报告，返回 markdown 字符串"""
    tools = detect_tools()
    lines = ["### 第三方工具链检测", ""]
    lines.append("| 工具 | 状态 | 用途 |")
    lines.append("|------|------|------|")
    lines.append(f"| Bandit | {'✅ 已安装' if tools['bandit'] else '⬜ 未安装'} | Python 安全扫描 |")
    lines.append(f"| Ruff | {'✅ 已安装' if tools['ruff'] else '⬜ 未安装'} | Python 代码质量检查 |")
    lines.append(f"| pytest | {'✅ 已安装' if tools['pytest'] else '⬜ 未安装'} | 测试运行 |")
    lines.append("")
    lines.append("安装方式：`pip install bandit ruff pytest`")
    return "\n".join(lines)


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="DevFlow 工具链桥接层")
    parser.add_argument("--check", action="store_true", help="检测已安装的工具")
    parser.add_argument("--bandit", metavar="DIR", help="运行 Bandit 扫描")
    parser.add_argument("--ruff", metavar="DIR", help="运行 Ruff lint")
    parser.add_argument("--pytest", metavar="DIR", help="运行 pytest")
    args = parser.parse_args()

    if args.check:
        t = detect_tools()
        for k, v in t.items():
            print(f"{k}: {'✅' if v else '❌'}")
    elif args.bandit:
        ok, out = run_bandit(args.bandit)
        print(out)
        sys.exit(0 if ok else 1)
    elif args.ruff:
        ok, out = run_ruff(args.ruff)
        print(out)
        sys.exit(0 if ok else 1)
    elif args.pytest:
        ok, out = run_pytest(args.pytest)
        print(out)
        sys.exit(0 if ok else 1)
    else:
        print(make_toolchain_report("."))
