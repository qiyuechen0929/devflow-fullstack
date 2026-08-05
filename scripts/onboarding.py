#!/usr/bin/env python3
"""
DevFlow - 新成员项目导览
自动生成新成员上手指南：项目结构、入口文件、环境要求、启动方式、关键模块
Usage: python onboarding.py --dir .
       python onboarding.py --dir . --output ONBOARDING.md
"""

import argparse
import json
import os
import subprocess
import sys
from pathlib import Path

IGNORE_DIRS = {"node_modules", ".git", "__pycache__", "dist", "build", ".next",
               "target", "vendor", ".venv", "venv"}


def find_entry_points(project_dir):
    """查找项目入口文件"""
    p = Path(project_dir)
    entries = []

    # 常见入口文件
    for name in ["main.py", "app.py", "index.py", "manage.py", "server.py",
                 "index.js", "index.ts", "app.js", "app.ts", "main.js",
                 "main.ts", "server.js", "server.ts", "entrypoint.py",
                 "cli.py", "run.py"]:
        if (p / name).exists():
            entries.append(name)

    # package.json 的 scripts
    if (p / "package.json").exists():
        try:
            pkg = json.loads((p / "package.json").read_text(encoding="utf-8"))
            scripts = pkg.get("scripts", {})
            if scripts:
                entries.append(f"package.json scripts: {', '.join(list(scripts.keys())[:5])}")
        except Exception:
            pass

    # pyproject.toml
    if (p / "pyproject.toml").exists():
        entries.append("pyproject.toml")

    return entries


def get_env_requirements(project_dir):
    """获取环境要求"""
    p = Path(project_dir)
    reqs = []

    if (p / "requirements.txt").exists():
        reqs.append("Python 依赖: requirements.txt")
    if (p / "pyproject.toml").exists():
        reqs.append("Python 项目: pyproject.toml")
    if (p / "package.json").exists():
        reqs.append("Node.js 项目: package.json")
    if (p / "Dockerfile").exists():
        reqs.append("Docker 镜像: Dockerfile")
    if (p / "docker-compose.yml").exists():
        reqs.append("Docker Compose: docker-compose.yml")
    if (p / ".env.example").exists():
        reqs.append("环境变量模板: .env.example")
    if (p / "Makefile").exists():
        reqs.append("构建工具: Makefile")

    return reqs


def find_key_modules(project_dir):
    """识别关键模块"""
    p = Path(project_dir)
    modules = []

    for root, dirs, files in os.walk(p):
        dirs[:] = [d for d in dirs if d not in IGNORE_DIRS and not d.startswith(".")]
        depth = root.replace(str(p), "").count(os.sep)
        if depth > 2:
            continue
        for f in files:
            if f.endswith((".py", ".js", ".ts", ".java", ".go")):
                rel = os.path.relpath(os.path.join(root, f), p)
                # 忽略测试、配置、脚本自身
                if any(x in rel.lower() for x in ("test", "spec", "config", "setup", "devflow")):
                    continue
                if len(modules) < 15:
                    modules.append(rel)

    return modules


def get_how_to_run(project_dir):
    """推断运行方式"""
    p = Path(project_dir)
    run_commands = []

    if (p / "Makefile").exists():
        run_commands.append("make start")
    if (p / "docker-compose.yml").exists():
        run_commands.append("docker-compose up")
    if (p / "package.json").exists():
        run_commands.append("npm install && npm start")
    if (p / "requirements.txt").exists() or (p / "pyproject.toml").exists():
        if (p / "manage.py").exists():
            run_commands.append("pip install -r requirements.txt && python manage.py runserver")
        elif (p / "app.py").exists():
            run_commands.append("pip install -r requirements.txt && python app.py")
        else:
            run_commands.append("pip install -r requirements.txt")
    if (p / "main.py").exists():
        run_commands.append("python main.py")

    return run_commands or ["（未检测到明确启动方式，请查阅 README）"]


def main():
    parser = argparse.ArgumentParser(description="DevFlow 新成员项目导览")
    parser.add_argument("--dir", default=".", help="项目目录")
    parser.add_argument("--output", help="输出为 Markdown 文件")
    parser.add_argument("--json", action="store_true", help="JSON 输出")
    args = parser.parse_args()

    project_dir = os.path.abspath(args.dir)
    p = Path(project_dir)
    if not p.is_dir():
        print(f"错误: {project_dir} 不是目录")
        sys.exit(1)

    report = {
        "project": p.name,
        "path": project_dir,
        "entry_points": find_entry_points(project_dir),
        "env_requirements": get_env_requirements(project_dir),
        "run_commands": get_how_to_run(project_dir),
        "key_modules": find_key_modules(project_dir),
        "has_readme": (p / "README.md").exists(),
        "has_docs": (p / "docs").is_dir(),
        "has_tests": any(x in [d.name for d in p.iterdir() if d.is_dir()] for x in ("tests", "test", "__tests__")),
    }

    if args.json:
        print(json.dumps(report, ensure_ascii=False, indent=2))
        return

    from datetime import datetime as _dt
    now_str = _dt.now().strftime('%Y-%m-%d')

    lines = []
    lines.append(f"# {report['project']} - 新成员导览")
    lines.append("")
    lines.append(f"> 自动生成于 {now_str}")
    lines.append("")
    lines.append("## 项目位置")
    lines.append("")
    lines.append(report['path'])
    lines.append("")
    lines.append("## 入口文件")
    lines.append("")
    if report['entry_points']:
        for e in report['entry_points']:
            lines.append("- " + e)
    else:
        lines.append("- 未检测到")
    lines.append("")
    lines.append("## 环境要求")
    lines.append("")
    if report['env_requirements']:
        for e in report['env_requirements']:
            lines.append("- " + e)
    else:
        lines.append("- 无")
    lines.append("")
    lines.append("## 启动方式")
    lines.append("")
    for c in report['run_commands']:
        lines.append("```bash")
        lines.append(c)
        lines.append("```")
    lines.append("")
    lines.append("## 关键模块")
    lines.append("")
    for m in report['key_modules']:
        lines.append("- `" + m + "`")
    lines.append("")
    lines.append("## 其他")
    lines.append("")
    lines.append("- 有 README: " + ('✅' if report['has_readme'] else '❌'))
    lines.append("- 有文档目录: " + ('✅' if report['has_docs'] else '❌'))
    lines.append("- 有测试目录: " + ('✅' if report['has_tests'] else '❌'))
    markdown = "\n".join(lines)

    if args.output:
        Path(args.output).write_text(markdown, encoding="utf-8")
        print(f"导览已保存: {args.output}")
    else:
        print(markdown)


if __name__ == "__main__":
    main()
