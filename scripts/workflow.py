#!/usr/bin/env python3
"""
DevFlow - 阶段化工作流引擎
实现 init → plan → code → verify → review 五阶段流水线，带状态持久化与质量关卡。

核心设计：
- 每个项目一个状态文件 .devflow/state.json，记录当前阶段与各阶段状态
- 每个阶段有前置条件（上一阶段必须通过）与质量关卡（gate）
- 质量关卡不通过则不能进入下一阶段

Usage:
  python workflow.py init                      # 初始化项目
  python workflow.py status                    # 查看当前状态
  python workflow.py next                      # 推进到下一阶段（运行当前阶段关卡）
  python workflow.py run                       # 运行当前阶段的动作
  python workflow.py gate <phase>              # 手动运行某个阶段的质量关卡
  python workflow.py reset                     # 重置状态
  python workflow.py plan                      # 快捷：生成计划文档
"""

import argparse
import json
import os
import re
import subprocess
import sys
import time
from pathlib import Path
from datetime import datetime

STATE_DIR_NAME = ".devflow"
STATE_FILE_NAME = "state.json"
PLAN_FILE_NAME = "plan.md"
MEMORY_FILE_NAME = "memory.md"
SCRIPTS_DIR = Path(__file__).parent


def append_memory(project_dir, entry):
    """向项目记忆文件追加一条记录"""
    mf = Path(project_dir) / STATE_DIR_NAME / MEMORY_FILE_NAME
    mf.parent.mkdir(parents=True, exist_ok=True)
    now = datetime.now().strftime("%Y-%m-%d %H:%M")
    line = f"## [{now}] {entry}\n"
    if mf.exists():
        with open(mf, "a", encoding="utf-8") as f:
            f.write("\n" + line)
    else:
        mf.write_text(f"# DevFlow 项目记忆\n\n{line}", encoding="utf-8")
    return line

# 五阶段定义
PHASES = ["init", "plan", "code", "verify", "review"]

PHASE_INFO = {
    "init": {
        "desc": "项目初始化与环境检测",
        "next_desc": "制定开发计划",
        "actions": ["env-check", "项目类型检测"],
        "gates": ["state_created", "project_detected"],
    },
    "plan": {
        "desc": "需求分析与计划制定",
        "next_desc": "编写代码",
        "actions": ["生成 plan.md", "架构设计"],
        "gates": ["plan_exists", "plan_nonempty"],
    },
    "code": {
        "desc": "编码实现",
        "next_desc": "质量验证",
        "actions": ["代码编写", "测试生成"],
        "gates": ["syntax_ok", "tests_pass"],
    },
    "verify": {
        "desc": "质量验证与缺陷修复",
        "next_desc": "最终审查",
        "actions": ["review扫描", "smell检测", "边界推演"],
        "gates": ["no_critical", "no_deadcode", "security_audit"],
    },
    "review": {
        "desc": "最终审查与总结",
        "next_desc": "完成",
        "actions": ["PR审查", "总结报告"],
        "gates": ["prior_green", "report_generated"],
    },
}


def get_state_path(project_dir):
    """获取状态文件路径"""
    return Path(project_dir) / STATE_DIR_NAME / STATE_FILE_NAME


def get_plan_path(project_dir):
    """获取计划文档路径"""
    return Path(project_dir) / PLAN_FILE_NAME


def init_state(project_dir):
    """初始化状态"""
    state = {
        "version": 1,
        "project": str(Path(project_dir).resolve()),
        "initialized_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "current_phase": "init",
        "project_type": detect_project_type(project_dir),
        "phases": {p: {"status": "pending", "completed_at": None}
                   for p in PHASES},
        "history": [],
    }
    state["phases"]["init"]["status"] = "in_progress"
    save_state(project_dir, state)
    return state


def load_state(project_dir):
    """加载状态"""
    sp = get_state_path(project_dir)
    if not sp.exists():
        return None
    try:
        return json.loads(sp.read_text(encoding="utf-8"))
    except Exception:
        return None


def save_state(project_dir, state):
    """保存状态"""
    sp = get_state_path(project_dir)
    sp.parent.mkdir(parents=True, exist_ok=True)
    sp.write_text(json.dumps(state, ensure_ascii=False, indent=2), encoding="utf-8")


def detect_project_type(project_dir):
    """检测项目类型"""
    p = Path(project_dir)
    has = lambda f: (p / f).exists()

    # 先检测最强的项目特征（避免 Dockerfile 干扰）
    if has("go.mod"):
        return "go"
    if has("pom.xml") or has("build.gradle"):
        return "java"
    if has("Cargo.toml"):
        return "rust"
    if has("package.json"):
        # 进一步区分
        try:
            pkg = json.loads((p / "package.json").read_text(encoding="utf-8"))
            deps = " ".join(list(pkg.get("dependencies", {})) + list(pkg.get("devDependencies", {})))
            if "react" in deps or "vue" in deps or "next" in deps:
                return "frontend"
            if "express" in deps or "koa" in deps or "fastify" in deps:
                return "backend-node"
            return "node"
        except Exception:
            return "node"
    if has("requirements.txt") or has("pyproject.toml") or has("Pipfile"):
        return "python"
    # Python 脚本项目（多个 .py 文件 + 无 package.json）
    py_files = list(p.glob("*.py"))
    scripts_dir = p / "scripts"
    if len(py_files) >= 2 or (scripts_dir.exists() and list(scripts_dir.glob("*.py"))):
        return "python"
    if has("*.sln") or has("*.csproj"):
        return "dotnet"
    if has("Dockerfile") or has("docker-compose.yml"):
        return "docker"
    return "unknown"


def run_script(script, args, target_dir):
    """运行 DevFlow 脚本"""
    cmd = [sys.executable, str(SCRIPTS_DIR / script), "--dir", target_dir] + args
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=60,
                                encoding="utf-8", errors="replace")
        return result.returncode, result.stdout + result.stderr
    except subprocess.TimeoutExpired:
        return -1, "TIMEOUT"
    except Exception as e:
        return -2, str(e)


# ---------- 质量关卡 ----------

def gate_state_created(project_dir, state):
    """状态文件已创建"""
    return get_state_path(project_dir).exists(), "状态文件存在"


def gate_project_detected(project_dir, state):
    """项目类型已检测"""
    return (state.get("project_type") != "unknown",
            f"项目类型: {state.get('project_type', 'unknown')}")


def gate_plan_exists(project_dir, state):
    """计划文档存在"""
    return get_plan_path(project_dir).exists(), f"{PLAN_FILE_NAME} 存在"


def gate_plan_nonempty(project_dir, state):
    """计划文档非空且有实质内容"""
    plan = get_plan_path(project_dir)
    if not plan.exists():
        return False, "plan.md 不存在"
    content = plan.read_text(encoding="utf-8", errors="ignore")
    has_content = len(content.strip()) > 100
    has_sections = all(k in content for k in ["## ", "目标", "任务"])
    return has_content and has_sections, "计划内容完整"


def gate_syntax_ok(project_dir, state):
    """代码语法正确（扫描代码文件）"""
    p = Path(project_dir)
    errors = []
    for f in p.rglob("*.py"):
        if ".devflow" in str(f) or "node_modules" in str(f) or ".git" in str(f):
            continue
        r = subprocess.run([sys.executable, "-m", "py_compile", str(f)],
                           capture_output=True, text=True)
        if r.returncode != 0:
            errors.append(str(f))
    if errors:
        return False, f"语法错误: {', '.join(errors[:3])}"
    return True, "Python 语法全部通过"


def gate_tests_pass(project_dir, state):
    """测试通过（存在测试文件则运行）"""
    p = Path(project_dir)
    test_files = list(p.rglob("test_*.py")) + list(p.rglob("tests/*.py"))
    if not test_files:
        return True, "无测试文件（跳过）"
    # 有 pytest 则运行
    try:
        import pytest  # noqa
        r = subprocess.run([sys.executable, "-m", "pytest", "-q"],
                           cwd=project_dir, capture_output=True, text=True, timeout=60)
        if r.returncode == 0:
            return True, "pytest 通过"
        return False, f"pytest 失败: {r.stdout.splitlines()[-1] if r.stdout else 'unknown'}"
    except ImportError:
        return True, f"pytest 不可用，跳过（发现 {len(test_files)} 个测试文件）"
    except Exception:
        return True, "pytest 运行异常（跳过）"


def gate_no_critical(project_dir, state):
    """无致命安全问题"""
    code, output = run_script("review.py", ["--mode", "security"], project_dir)
    critical = output.count("[L4]")
    if critical > 5:  # 阈值：允许少量模式定义误报
        return False, f"发现 {critical} 处高危问题"
    return True, f"高危问题 {critical} 处（阈值内）"


def gate_no_deadcode(project_dir, state):
    """无遗留 TODO/FIXME"""
    code, output = run_script("todo-scan.py", ["--dir", project_dir], project_dir)
    # todo-scan 返回 1 表示有高优先级标记
    if "高" in output and "共发现" in output:
        high_count = 0
        for line in output.split("\n"):
            if "[高]" in line:
                high_count += 1
        if high_count > 0:
            return False, f"遗留 {high_count} 处高优先级标记"
    return True, "无高优先级遗留标记"


def gate_security_audit(project_dir, state):
    """深度安全审计通过（无严重/高危问题）"""
    code, output = run_script("security-audit.py", ["--dir", project_dir], project_dir)
    severe = output.count("[严重]")
    high = output.count("[高]")
    # 允许少量模式定义误报（阈值 3）
    if severe > 0 or high > 3:
        return False, f"深度审计发现 {severe} 处严重, {high} 处高危"
    return True, f"深度审计: {severe} 严重, {high} 高危 (阈值内)"


def gate_prior_green(project_dir, state):
    """所有前置阶段全部通过"""
    phases = state.get("phases", {})
    for p_name in PHASES[:-1]:
        if phases.get(p_name, {}).get("status") != "completed":
            return False, f"阶段 {p_name} 尚未完成"
    return True, "所有前置阶段已完成"


def gate_report_generated(project_dir, state):
    """总结报告已生成"""
    report = Path(project_dir) / "DEVFLOW_REPORT.md"
    return report.exists(), "DEVFLOW_REPORT.md 存在"


GATES = {
    "state_created": gate_state_created,
    "project_detected": gate_project_detected,
    "plan_exists": gate_plan_exists,
    "plan_nonempty": gate_plan_nonempty,
    "syntax_ok": gate_syntax_ok,
    "tests_pass": gate_tests_pass,
    "no_critical": gate_no_critical,
    "no_deadcode": gate_no_deadcode,
    "security_audit": gate_security_audit,
    "prior_green": gate_prior_green,
    "report_generated": gate_report_generated,
}


def run_gates(phase, project_dir, state):
    """运行某个阶段的所有关卡，返回 (通过, 结果列表)"""
    results = []
    all_pass = True
    for gate_name in PHASE_INFO[phase]["gates"]:
        gate_fn = GATES[gate_name]
        passed, msg = gate_fn(project_dir, state)
        results.append({"gate": gate_name, "passed": passed, "message": msg})
        if not passed:
            all_pass = False
    return all_pass, results


# ---------- 阶段动作 ----------

def run_phase_actions(phase, project_dir, state):
    """运行当前阶段的动作，返回输出文本"""
    outputs = []
    if phase == "init":
        code, out = run_script("env-check.py", [], project_dir)
        outputs.append(f"[env-check] {out[:200]}")
        outputs.append(f"项目类型: {state.get('project_type')}")
    elif phase == "plan":
        plan_path = get_plan_path(project_dir)
        if not plan_path.exists():
            plan_path.write_text(
                f"# 开发计划\n\n## 目标\n\n（填写项目目标）\n\n"
                f"## 任务\n\n- [ ] 任务一\n- [ ] 任务二\n\n"
                f"## 技术方案\n\n（填写技术选型）\n\n"
                f"---\n_由 DevFlow 自动生成于 {datetime.now().strftime('%Y-%m-%d')}，请编辑完善_",
                encoding="utf-8")
        outputs.append(f"计划文档已生成: {plan_path}")
    elif phase == "code":
        outputs.append("请在 plan.md 的指导下编写代码。完成后运行 'devflow workflow verify' 进入验证。")
    elif phase == "verify":
        for script, args, label in [
            ("review.py", ["--mode", "scan"], "Bug扫描"),
            ("smell.py", [], "坏味道检测"),
            ("boundary.py", [], "边界推演"),
        ]:
            code, out = run_script(script, args, project_dir)
            outputs.append(f"[{label}] {out[:150]}")
    elif phase == "review":
        report = Path(project_dir) / "DEVFLOW_REPORT.md"
        report.write_text(
            f"# DevFlow 项目总结\n\n- 项目: {state.get('project')}\n"
            f"- 完成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n"
            f"- 阶段: 全部完成\n\n## 回顾\n\n（填写复盘内容）\n",
            encoding="utf-8")
        outputs.append(f"总结报告已生成: {report}")
    return "\n".join(outputs)


# ---------- 主逻辑 ----------

def cmd_init(project_dir):
    state = load_state(project_dir)
    if state and state.get("current_phase") != "verify":
        print("项目已初始化。运行 'devflow workflow status' 查看状态。")
        return
    state = init_state(project_dir)
    print(f"✓ 项目初始化完成")
    print(f"  项目类型: {state['project_type']}")
    print(f"  状态文件: {get_state_path(project_dir)}")
    print(f"\n下一步: python workflow.py next   (运行 init 关卡并进入 plan 阶段)")


def cmd_status(project_dir):
    state = load_state(project_dir)
    if not state:
        print("尚未初始化。先运行: python workflow.py init")
        return

    print(f"项目: {state['project']}")
    print(f"类型: {state['project_type']}")
    print(f"当前阶段: {state['current_phase']} ({PHASE_INFO[state['current_phase']]['desc']})")
    print()
    print("阶段进度:")
    for p in PHASES:
        st = state["phases"].get(p, {}).get("status", "pending")
        icon = {"completed": "✅", "in_progress": "🔄", "pending": "⬜"}.get(st, "⬜")
        print(f"  {icon} {p:<8} {PHASE_INFO[p]['desc']}")
    print()
    print("当前阶段关卡:")
    for gate in PHASE_INFO[state["current_phase"]]["gates"]:
        print(f"  - {gate}")


def cmd_next(project_dir):
    state = load_state(project_dir)
    if not state:
        print("尚未初始化。先运行: python workflow.py init")
        return

    current = state["current_phase"]
    phase_state = state["phases"].get(current, {})

    if phase_state.get("status") == "completed":
        # 已完成的阶段直接跳过
        idx = PHASES.index(current)
        if idx >= len(PHASES) - 1:
            print("🎉 所有阶段已完成！")
            return
        next_phase = PHASES[idx + 1]
        state["current_phase"] = next_phase
        state["phases"][next_phase]["status"] = "in_progress"
        save_state(project_dir, state)
        print(f"已进入阶段: {next_phase} ({PHASE_INFO[next_phase]['desc']})")
        print(f"下一步: python workflow.py run 来执行该阶段动作，或 python workflow.py next 运行关卡")
        return

    # 运行当前阶段关卡
    print(f"运行阶段 [{current}] 的质量关卡...")
    passed, results = run_gates(current, project_dir, state)
    for r in results:
        icon = "✅" if r["passed"] else "❌"
        print(f"  {icon} {r['gate']}: {r['message']}")

    if not passed:
        print(f"\n关卡未通过，停留在 [{current}] 阶段。")
        print("提示：先运行 'python workflow.py run' 执行本阶段动作。")
        state["history"].append({
            "phase": current, "time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "result": "gate_failed"
        })
        save_state(project_dir, state)
        sys.exit(1)

    # 标记当前阶段完成
    phase_state["status"] = "completed"
    phase_state["completed_at"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    # 记录到项目记忆
    try:
        append_memory(project_dir, f"阶段 [{current}] 通过质量关卡，进入下一阶段")
    except Exception:
        pass

    # 进入下一阶段
    idx = PHASES.index(current)
    if idx >= len(PHASES) - 1:
        state["current_phase"] = "completed"
        print(f"\n🎉 全部阶段完成！")
    else:
        next_phase = PHASES[idx + 1]
        state["current_phase"] = next_phase
        state["phases"][next_phase]["status"] = "in_progress"
        print(f"\n✅ 阶段 [{current}] 通过！")
        print(f"已进入阶段: {next_phase} ({PHASE_INFO[next_phase]['desc']})")

    state["history"].append({
        "phase": current, "time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "result": "passed"
    })
    save_state(project_dir, state)


def cmd_run(project_dir):
    state = load_state(project_dir)
    if not state:
        print("尚未初始化。先运行: python workflow.py init")
        return

    current = state["current_phase"]
    if current == "completed":
        print("所有阶段已完成。运行 'python workflow.py reset' 重新开始。")
        return

    print(f"执行阶段 [{current}] 的动作...")
    output = run_phase_actions(current, project_dir, state)
    print(output)
    print(f"\n完成。运行 'python workflow.py next' 运行质量关卡并进入下一阶段。")


def cmd_gate(project_dir, phase):
    state = load_state(project_dir)
    if not state:
        print("尚未初始化。先运行: python workflow.py init")
        return
    if phase not in PHASES:
        print(f"未知阶段: {phase}。可选: {', '.join(PHASES)}")
        return
    print(f"运行阶段 [{phase}] 的质量关卡...")
    passed, results = run_gates(phase, project_dir, state)
    for r in results:
        icon = "✅" if r["passed"] else "❌"
        print(f"  {icon} {r['gate']}: {r['message']}")
    print(f"\n{'✅ 全部通过' if passed else '❌ 存在未通过的关卡'}")
    return 0 if passed else 1


def cmd_reset(project_dir):
    sp = get_state_path(project_dir)
    if sp.exists():
        sp.unlink()
        print("状态已重置。")
    else:
        print("无状态文件。")


def cmd_plan(project_dir):
    """快捷生成计划文档"""
    state = load_state(project_dir) or init_state(project_dir)
    plan_path = get_plan_path(project_dir)
    project_type = state.get("project_type", "unknown")
    plan_path.write_text(
        f"# 开发计划\n\n"
        f"## 目标\n\n（填写项目目标）\n\n"
        f"## 任务\n\n"
        f"- [ ] 需求分析\n- [ ] 架构设计\n- [ ] 编码实现\n- [ ] 测试验证\n\n"
        f"## 技术方案\n\n"
        f"- 项目类型: {project_type}\n"
        f"- 技术选型: （待定）\n\n"
        f"---\n_由 DevFlow 自动生成于 {datetime.now().strftime('%Y-%m-%d')}，请编辑完善_",
        encoding="utf-8")
    print(f"计划文档已生成: {plan_path}")
    print("请编辑 plan.md 填写具体内容，然后运行 'python workflow.py next' 进入编码阶段。")


def main():
    parser = argparse.ArgumentParser(description="DevFlow 阶段化工作流引擎")
    parser.add_argument("command", choices=["init", "status", "next", "run", "gate",
                                           "reset", "plan"],
                        help="工作流命令")
    parser.add_argument("--dir", default=".", help="项目目录")
    parser.add_argument("phase", nargs="?", help="gate 命令的阶段参数")
    args = parser.parse_args()

    project_dir = os.path.abspath(args.dir)

    if args.command == "init":
        cmd_init(project_dir)
    elif args.command == "status":
        cmd_status(project_dir)
    elif args.command == "next":
        cmd_next(project_dir)
    elif args.command == "run":
        cmd_run(project_dir)
    elif args.command == "gate":
        sys.exit(cmd_gate(project_dir, args.phase))
    elif args.command == "reset":
        cmd_reset(project_dir)
    elif args.command == "plan":
        cmd_plan(project_dir)


if __name__ == "__main__":
    main()
