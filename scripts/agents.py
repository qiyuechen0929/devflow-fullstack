#!/usr/bin/env python3
"""
DevFlow - 多 Agent 协作层
将现有 DevFlow 脚本包装为 5 个专业角色，支持串行流水线与并行执行。

角色：
  pm         项目管理    - 规划任务、协调各角色、生成计划
  architect  架构师      - 分析项目结构、生成架构图、边界推演
  developer  开发者      - 生成测试、生成文档、解释代码
  qa         质量保证    - Bug扫描、坏味道检测、竞态分析
  reviewer   审查者      - 安全审查、代码复杂度、TODO扫描

Usage:
  python agents.py --team all            # 串行运行全部角色
  python agents.py --team qa,reviewer    # 运行指定角色
  python agents.py --role pm --task plan # 单独运行一个角色
  python agents.py --parallel            # 并行运行独立角色
  python agents.py --list                # 列出所有角色
"""

import argparse
import json
import os
import subprocess
import sys
import time
from pathlib import Path
from datetime import datetime

# 确保可 import 同目录模块（llm 等）
sys.path.insert(0, str(Path(__file__).resolve().parent))

SCRIPTS_DIR = Path(__file__).parent

# 角色定义：每个角色包含要执行的脚本任务列表
ROLES = {
    "pm": {
        "desc": "项目管理 - 规划任务、协调执行",
        "tasks": [
            {"script": "git-helper.py", "args": ["--mode", "commit"],
             "desc": "生成 commit 建议"},
            {"script": "git-stats.py", "args": ["--dir"], "desc": "Git 提交统计"},
        ],
    },
    "architect": {
        "desc": "架构师 - 分析结构、生成架构图",
        "tasks": [
            {"script": "arch-gen.py", "args": ["--dir", "--type", "dependency"],
             "desc": "依赖关系架构图"},
            {"script": "boundary.py", "args": ["--file"], "desc": "边界用例推演"},
        ],
    },
    "developer": {
        "desc": "开发者 - 生成测试与文档",
        "tasks": [
            {"script": "testgen.py", "args": ["--file", "--framework", "pytest"],
             "desc": "生成测试用例"},
            {"script": "docgen.py", "args": ["--file", "--mode", "all"],
             "desc": "生成文档"},
            {"script": "explain.py", "args": ["--file"], "desc": "解释代码"},
        ],
    },
    "qa": {
        "desc": "质量保证 - 扫描 Bug 与代码坏味道",
        "tasks": [
            {"script": "review.py", "args": ["--mode", "scan"], "desc": "Bug 扫描"},
            {"script": "smell.py", "args": [], "desc": "坏味道检测"},
            {"script": "racecheck.py", "args": ["--file"], "desc": "竞态分析"},
        ],
    },
    "reviewer": {
        "desc": "审查者 - 安全与质量审查",
        "tasks": [
            {"script": "review.py", "args": ["--mode", "security"], "desc": "安全审查"},
            {"script": "complexity.py", "args": ["--file"], "desc": "复杂度分析"},
            {"script": "todo-scan.py", "args": ["--dir"], "desc": "TODO 标记扫描"},
            {"script": "refactor.py", "args": ["--dir"], "desc": "重构建议"},
        ],
    },
    "security": {
        "desc": "安全专家 - 深度安全审计",
        "tasks": [
            {"script": "security-audit.py", "args": ["--dir"], "desc": "深度安全审计"},
            {"script": "review.py", "args": ["--mode", "security"], "desc": "安全模式扫描"},
            {"script": "pr-tool.py", "args": ["--diff"], "desc": "PR 安全检查"},
        ],
    },
    "devops": {
        "desc": "运维 - 环境与部署检查",
        "tasks": [
            {"script": "doctor.py", "args": ["--dir"], "desc": "项目健康诊断"},
            {"script": "env-check.py", "args": ["--dir"], "desc": "环境检查"},
            {"script": "deploy.py", "args": ["--list"], "desc": "部署平台检查"},
        ],
    },
    "onboarder": {
        "desc": "导览 - 新成员项目导览",
        "tasks": [
            {"script": "onboarding.py", "args": ["--dir"], "desc": "生成项目导览"},
            {"script": "code-map.py", "args": ["--dir"], "desc": "代码地图"},
            {"script": "docgen.py", "args": ["--dir", "--mode", "readme"], "desc": "生成 README"},
        ],
    },
}


def find_project_file(target_dir, exts=(".py", ".js", ".ts", ".jsx", ".tsx", ".java", ".go", ".c", ".cpp", ".rs", ".rb")):
    """在目录里找一个代表性的代码文件"""
    p = Path(target_dir)
    for f in sorted(p.iterdir()):
        if f.is_file() and f.suffix in exts and "workflow" not in f.name and "agents" not in f.name:
            return str(f)
    # 找 scripts 目录
    scripts_dir = p / "scripts"
    if scripts_dir.exists():
        for f in sorted(scripts_dir.iterdir()):
            if f.is_file() and f.suffix in exts:
                return str(f)
    return None


def run_task(task, target_dir, file_path=None):
    """执行单个任务"""
    script = SCRIPTS_DIR / task["script"]
    args = []
    for a in task.get("args", []):
        if a == "--dir":
            args.extend(["--dir", target_dir])
        elif a == "--file":
            if file_path:
                args.extend(["--file", file_path])
        else:
            args.append(a)

    if not script.exists():
        return {"task": task["desc"], "ok": False, "output": f"脚本不存在: {task['script']}"}

    cmd = [sys.executable, str(script)] + args
    try:
        start = time.time()
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=45,
                                encoding="utf-8", errors="replace")
        elapsed = time.time() - start
        output = (result.stdout + result.stderr).strip()
        # 截断过长输出
        if len(output) > 300:
            output = output[:300] + "..."
        return {
            "task": task["desc"],
            "script": task["script"],
            "ok": result.returncode in (0, 1),
            "output": output,
            "elapsed": round(elapsed, 1),
        }
    except subprocess.TimeoutExpired:
        return {"task": task["desc"], "script": task["script"], "ok": False,
                "output": "TIMEOUT", "elapsed": 45}
    except Exception as e:
        return {"task": task["desc"], "script": task["script"], "ok": False,
                "output": str(e), "elapsed": 0}


def run_role(role_name, target_dir, file_path=None):
    """运行一个角色的所有任务"""
    role = ROLES[role_name]
    results = []
    print(f"\n{'='*50}")
    print(f"👤 角色 [{role_name}] {role['desc']}")
    print(f"{'='*50}")

    for task in role["tasks"]:
        print(f"  · {task['desc']}...", end=" ", flush=True)
        r = run_task(task, target_dir, file_path)
        icon = "✅" if r["ok"] else "⚠️"
        print(f"{icon} ({r['elapsed']}s)")
        results.append(r)

    passed = sum(1 for r in results if r["ok"])
    print(f"  → {passed}/{len(results)} 项通过")
    return {"role": role_name, "desc": role["desc"], "results": results,
            "passed": passed, "total": len(results)}


def llm_synthesize(role_results, target_dir):
    """使用 LLM 汇总各角色输出，给出整体分析。LLM 不可用时返回 None。"""
    try:
        import llm
    except ImportError:
        return None
    if not llm.is_available():
        return None

    # 汇总各角色输出
    parts = []
    for rr in role_results:
        role_out = []
        for r in rr["results"]:
            role_out.append(f"- {r['task']}: {r['output'][:200]}")
        parts.append(f"## 角色 {rr['role']}\n" + "\n".join(role_out))
    summary = "\n\n".join(parts)

    prompt = (
        f"以下是 DevFlow 多角色工具对项目 {target_dir} 扫描的原始输出。\n"
        f"请作为资深代码审查负责人，给出：\n"
        f"1. 最重要的 3 个问题（按严重程度排序）\n"
        f"2. 每个问题的修复建议\n"
        f"3. 总体评价（1-5 分）\n"
        f"要求说人话，不堆术语。\n\n"
        f"扫描输出：\n{summary[:12000]}"
    )
    try:
        return llm.chat(prompt, system="你是 DevFlow 的代码审查负责人，善于汇总工具输出并给出可执行的结论。")
    except Exception as e:
        return f"[LLM 调用失败] {e}"


def generate_report(role_results, target_dir, total_time):
    """生成多 Agent 协作报告"""
    lines = []
    lines.append("# DevFlow 多 Agent 协作报告")
    lines.append("")
    lines.append(f"- **目标**: `{target_dir}`")
    lines.append(f"- **时间**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    lines.append(f"- **耗时**: {total_time:.1f}s")
    lines.append("")

    for rr in role_results:
        lines.append(f"## 👤 {rr['role']} - {rr['desc']}")
        lines.append("")
        for r in rr["results"]:
            icon = "✅" if r["ok"] else "⚠️"
            lines.append(f"- {icon} **{r['task']}** ({r['elapsed']}s)")
            if r.get("output"):
                lines.append(f"  ```")
                lines.append(f"  {r['output'][:200]}")
                lines.append(f"  ```")
        lines.append("")

    total_ok = sum(rr["passed"] for rr in role_results)
    total = sum(rr["total"] for rr in role_results)
    lines.append(f"## 总结: {total_ok}/{total} 项通过")
    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser(description="DevFlow 多 Agent 协作层")
    parser.add_argument("--team", help="角色列表，逗号分隔 (all=全部, 如 qa,reviewer)")
    parser.add_argument("--role", help="单独运行一个角色")
    parser.add_argument("--task", help="角色任务提示（供 AI 调用）")
    parser.add_argument("--dir", default=".", help="目标目录")
    parser.add_argument("--file", help="指定代码文件")
    parser.add_argument("--parallel", action="store_true", help="并行运行独立角色")
    parser.add_argument("--list", action="store_true", help="列出所有角色")
    parser.add_argument("--output", help="输出报告文件")
    parser.add_argument("--format", choices=["text", "json"], default="text")
    parser.add_argument("--llm", action="store_true",
                        help="用 LLM 汇总各角色输出并给出整体结论（需配置模型；未配置自动跳过）")
    args = parser.parse_args()

    if args.list:
        print("DevFlow 多 Agent 角色:")
        for name, role in ROLES.items():
            print(f"  {name:<12} {role['desc']}")
            for t in role["tasks"]:
                print(f"      · {t['desc']}")
        return

    target_dir = os.path.abspath(args.dir)
    if not os.path.isdir(target_dir):
        print(f"错误: {target_dir} 不是目录")
        sys.exit(1)

    # 自动找代码文件
    file_path = args.file or find_project_file(target_dir)
    if not file_path and args.team not in ("pm", "all"):
        file_path = find_project_file(target_dir, exts=(".py",))
    if file_path:
        print(f"代码文件: {file_path}")

    # 确定要运行的角色
    if args.role:
        team = [args.role]
    elif args.team:
        team = list(ROLES.keys()) if args.team == "all" else \
            [r.strip() for r in args.team.split(",") if r.strip() in ROLES]
    else:
        team = list(ROLES.keys())

    if not team:
        print("错误: 没有有效的角色。用 --list 查看。")
        sys.exit(1)

    print(f"运行 {len(team)} 个角色: {', '.join(team)}")

    start_total = time.time()
    role_results = []

    if args.parallel:
        # 并行模式：独立角色可同时跑（这里用简单轮询模拟并发，实际可换线程池）
        import concurrent.futures
        print("并行模式...")
        with concurrent.futures.ThreadPoolExecutor(max_workers=min(len(team), 3)) as pool:
            futures = {pool.submit(run_role, r, target_dir, file_path): r for r in team}
            for future in concurrent.futures.as_completed(futures):
                rr = future.result()
                role_results.append(rr)
        # 按 team 顺序重排
        role_results.sort(key=lambda x: team.index(x["role"]))
    else:
        # 串行模式
        for role_name in team:
            rr = run_role(role_name, target_dir, file_path)
            role_results.append(rr)

    total_time = time.time() - start_total

    if args.format == "json":
        report = {
            "target": target_dir,
            "total_time": round(total_time, 1),
            "roles": [
                {"role": rr["role"], "passed": rr["passed"], "total": rr["total"],
                 "results": rr["results"]}
                for rr in role_results
            ]
        }
        print(json.dumps(report, ensure_ascii=False, indent=2))
        return

    # 输出总结
    print(f"\n{'='*50}")
    print("协作总结:")
    for rr in role_results:
        icon = "✅" if rr["passed"] == rr["total"] else "⚠️"
        print(f"  {icon} {rr['role']:<12} {rr['passed']}/{rr['total']}")
    print(f"耗时: {total_time:.1f}s")

    # LLM 汇总（可选）
    if args.llm:
        synthesis = llm_synthesize(role_results, target_dir)
        if synthesis:
            print(f"\n{'='*50}")
            print("📝 LLM 整体结论:")
            print(f"{'='*50}")
            print(synthesis)
        else:
            print(f"\n[提示] 未配置 LLM，跳过整体结论。"
                  f"（配置方式：python model-manager.py --config --provider openai --api-key ...）")

    if args.output:
        report = generate_report(role_results, target_dir, total_time)
        if args.llm:
            synthesis = llm_synthesize(role_results, target_dir)
            if synthesis:
                report += f"\n\n## 📝 LLM 整体结论\n\n{synthesis}"
        Path(args.output).write_text(report, encoding="utf-8")
        print(f"报告已保存: {args.output}")


if __name__ == "__main__":
    main()
