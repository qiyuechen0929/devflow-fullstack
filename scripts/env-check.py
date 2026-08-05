#!/usr/bin/env python3
"""
DevFlow - Environment Checker
Usage: python env-check.py --dir .
"""

import argparse, os, sys, subprocess, platform, shutil
from pathlib import Path

def check_all(dirpath):
    results = []

    # OS
    results.append(f"系统: {platform.system()} {platform.release()} ({platform.machine()})")

    # Python
    v = sys.version.split()[0]
    results.append(f"Python: {v}")

    # Node
    node = shutil.which("node")
    if node:
        try:
            nv = subprocess.run(["node","-v"], capture_output=True, text=True).stdout.strip()
            results.append(f"Node.js: {nv}")
        except Exception: results.append("Node.js: 已安装(无法获取版本)")
    else: results.append("Node.js: 未安装 [X]")

    # Git
    git = shutil.which("git")
    results.append(f"Git: {'已安装' if git else '未安装 [X]'}")

    # Java
    java = shutil.which("java")
    if java:
        try:
            jv = subprocess.run(["java","-version"], capture_output=True, text=True, stderr=subprocess.STDOUT).stdout.split("\n")[0]
            results.append(f"Java: {jv}")
        except Exception: results.append("Java: 已安装")
    else: results.append("Java: 未安装")

    # Docker
    docker = shutil.which("docker")
    results.append(f"Docker: {'已安装' if docker else '未安装'}")

    # ─── Project Detection ───
    p = Path(dirpath)
    project_type = None

    if (p / "package.json").exists():
        import json
        try:
            pkg = json.loads((p/"package.json").read_text())
            deps = {**pkg.get("dependencies",{}), **pkg.get("devDependencies",{})}
            if "next" in deps: project_type = "Next.js"
            elif "react" in deps: project_type = "React"
            elif "vue" in deps: project_type = "Vue"
            elif "express" in deps: project_type = "Express"
            else: project_type = "Node.js"
        except Exception: project_type = "Node.js"

    elif (p / "pom.xml").exists(): project_type = "Java/Maven"
    elif (p / "build.gradle").exists(): project_type = "Java/Gradle"
    elif (p / "requirements.txt").exists() or (p / "pyproject.toml").exists():
        project_type = "Python"
    elif (p / "go.mod").exists(): project_type = "Go"
    elif (p / "Cargo.toml").exists(): project_type = "Rust"

    results.append(f"\n项目类型: {project_type or '未知'}")

    # Config files found
    configs = ["Dockerfile","docker-compose.yml",".env","Makefile","README.md",
               ".github/workflows",".eslintrc","tsconfig.json","tailwind.config.js"]
    for c in configs:
        if (p / c).exists():
            results.append(f"  [OK] {c}")

    # Missing recommended files
    recommended = [".gitignore","README.md"]
    missing = [r for r in recommended if not (p / r).exists()]
    if missing:
        results.append(f"\n建议添加: {', '.join(missing)}")

    return "\n".join(results)

def main():
    parser = argparse.ArgumentParser(description="Environment Checker")
    parser.add_argument("--dir", default=".")
    args = parser.parse_args()
    print(check_all(args.dir))

if __name__ == "__main__":
    main()
