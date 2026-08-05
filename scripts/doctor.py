#!/usr/bin/env python3
"""
DevFlow - 项目健康诊断
一键诊断项目健康状况：环境、结构、依赖、代码质量、安全
Usage: python doctor.py --dir .
       python doctor.py --dir . --json
"""

import argparse
import json
import os
import subprocess
import sys
from pathlib import Path

IGNORE_DIRS = {"node_modules", ".git", "__pycache__", "dist", "build", ".next",
               "target", "vendor", ".venv", "venv"}


def check_env():
    """检查开发环境"""
    checks = []
    try:
        v = subprocess.run([sys.executable, "--version"], capture_output=True, text=True, timeout=10)
        checks.append(("Python", v.stdout.strip() or v.stderr.strip(), True))
    except Exception:
        checks.append(("Python", "未安装", False))

    for tool in ("git", "node", "npm", "docker", "gcc"):
        try:
            r = subprocess.run([tool, "--version"], capture_output=True, text=True, timeout=10)
            ok = r.returncode == 0
            ver = r.stdout.strip().split("\n")[0] if ok else "未安装"
            checks.append((tool, ver, ok))
        except FileNotFoundError:
            checks.append((tool, "未安装", False))
        except Exception:
            checks.append((tool, "未知", False))
    return checks


def check_structure(project_dir):
    """检查项目结构完整性"""
    p = Path(project_dir)
    issues = []

    # 必备文件
    for f, name in [("README.md", "README"), (".gitignore", ".gitignore"), ("LICENSE", "LICENSE")]:
        if not (p / f).exists():
            issues.append(f"缺少 {name}")

    # 依赖文件
    has_pkg = (p / "package.json").exists()
    has_req = (p / "requirements.txt").exists()
    if not has_pkg and not has_req:
        issues.append("未发现依赖声明文件 (package.json / requirements.txt)")

    return issues


def check_code_quality(project_dir):
    """粗略评估代码质量"""
    p = Path(project_dir)
    total_lines = 0
    total_files = 0
    for root, dirs, files in os.walk(p):
        dirs[:] = [d for d in dirs if d not in IGNORE_DIRS]
        for f in files:
            if f.endswith((".py", ".js", ".ts", ".jsx", ".tsx", ".java", ".go", ".c", ".cpp")):
                total_files += 1
                try:
                    total_lines += len(Path(root, f).read_text(encoding="utf-8", errors="ignore").split("\n"))
                except Exception:
                    pass
    return total_files, total_lines


def main():
    parser = argparse.ArgumentParser(description="DevFlow 项目健康诊断")
    parser.add_argument("--dir", default=".", help="项目目录")
    parser.add_argument("--json", action="store_true", help="JSON 输出")
    args = parser.parse_args()

    project_dir = os.path.abspath(args.dir)
    p = Path(project_dir)
    if not p.is_dir():
        print(f"错误: {project_dir} 不是目录")
        sys.exit(1)

    report = {"project": project_dir}

    if args.json:
        env = [{"tool": t, "version": v, "ok": ok} for t, v, ok in check_env()]
        struct = check_structure(project_dir)
        files, lines = check_code_quality(project_dir)
        report = {
            "project": project_dir,
            "env": env,
            "structure_issues": struct,
            "code_files": files,
            "code_lines": lines,
        }
        print(json.dumps(report, ensure_ascii=False, indent=2))
        return

    print(f"🏥 DevFlow 健康诊断: {project_dir}\n")

    print("【1】开发环境")
    for tool, ver, ok in check_env():
        icon = "✅" if ok else "❌"
        print(f"  {icon} {tool:<10} {ver}")

    print("\n【2】项目结构")
    struct = check_structure(project_dir)
    if struct:
        for s in struct:
            print(f"  ⚠️  {s}")
    else:
        print("  ✅ 结构完整")

    files, lines = check_code_quality(project_dir)
    print(f"\n【3】代码规模")
    print(f"  代码文件: {files} 个")
    print(f"  总代码行: {lines} 行")

    ok_count = sum(1 for _, _, ok in check_env() if ok)
    print(f"\n总结: 环境 {ok_count}/6 项可用 | 结构 {'完整' if not struct else '有缺漏'}")
    if not struct and ok_count >= 4:
        print("结论: 项目健康状况良好 ✅")
    else:
        print("结论: 建议修复上述问题")
        sys.exit(1)


if __name__ == "__main__":
    main()
