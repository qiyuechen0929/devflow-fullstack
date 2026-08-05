#!/usr/bin/env python3
"""
DevFlow CLI - 统一命令行入口（模块化版本，支持 pip 安装）

用法: devflow <command> [options]
       python devflow_cli.py <command> [options]
"""

import os
import subprocess
import sys
from pathlib import Path

# 定位 scripts 目录：优先仓库内（开发模式），其次安装目录（pip 安装后）
_REPO_SCRIPTS = Path(__file__).resolve().parent / "scripts"

def _candidate_installed_dirs() -> list[Path]:
    """pip 安装后数据文件可能的位置（wheel 的 data 目录）"""
    candidates = []
    # 常规 site-packages 安装：<prefix>/share/devflow/scripts
    candidates.append(Path(sys.prefix) / "share" / "devflow" / "scripts")
    # user 安装（pip install --user）：~/.local/share/devflow/scripts
    user_base = os.environ.get("PYTHONUSERBASE")
    if user_base:
        candidates.append(Path(user_base) / "share" / "devflow" / "scripts")
    else:
        candidates.append(Path.home() / ".local" / "share" / "devflow" / "scripts")
    # 某些系统 data 目录不同
    try:
        import sysconfig
        candidates.append(Path(sysconfig.get_path("data")) / "share" / "devflow" / "scripts")
    except Exception:
        pass
    return candidates

def _scripts_dir() -> Path:
    if _REPO_SCRIPTS.exists():
        return _REPO_SCRIPTS
    for d in _candidate_installed_dirs():
        if d.exists():
            return d
    return _REPO_SCRIPTS  # 返回默认，运行时再报错

SCRIPTS_DIR = _scripts_dir()

COMMANDS = {
    "review": {
        "desc": "代码审查 (安全/逻辑/性能)",
        "script": "review.py",
        "example": "devflow review --mode security --dir ."
    },
    "explain": {
        "desc": "代码结构分析 (代码→人话需配合 AI)",
        "script": "explain.py",
        "example": "devflow explain --file main.py"
    },
    "testgen": {
        "desc": "测试模板生成",
        "script": "testgen.py",
        "example": "devflow testgen --file calculator.py --framework pytest"
    },
    "docgen": {
        "desc": "文档生成",
        "script": "docgen.py",
        "example": "devflow docgen --mode all --file main.py"
    },
    "smell": {
        "desc": "代码坏味道检测",
        "script": "smell.py",
        "example": "devflow smell --dir ."
    },
    "migrate": {
        "desc": "语法/语言规则转换",
        "script": "migrate.py",
        "example": "devflow migrate --from py2 --to py3 --dir src/"
    },
    "env": {
        "desc": "环境检查",
        "script": "env-check.py",
        "example": "devflow env --dir ."
    },
    "git": {
        "desc": "Git 辅助 (Commit/PR)",
        "script": "git-helper.py",
        "example": "devflow git --mode commit"
    },
    "clean": {
        "desc": "清理调试标记",
        "script": "clean-debug.py",
        "example": "devflow clean --dir src/"
    },
    "regex": {
        "desc": "正则表达式工具",
        "script": "regex.py",
        "example": "devflow regex --pattern '\\d+' --text 'abc123'"
    },
    "boundary": {
        "desc": "边界用例推演",
        "script": "boundary.py",
        "example": "devflow boundary --file main.py"
    },
    "racecheck": {
        "desc": "竞态条件分析",
        "script": "racecheck.py",
        "example": "devflow racecheck --file async.py"
    },
    "config": {
        "desc": "配置文件生成",
        "script": "config-gen.py",
        "example": "devflow config --type docker"
    },
    "a11y": {
        "desc": "无障碍审查",
        "script": "a11y.py",
        "example": "devflow a11y --file index.html"
    },
    "db": {
        "desc": "数据库查询优化",
        "script": "db-optimize.py",
        "example": "devflow db --file query.sql"
    },
    "full": {
        "desc": "全流程运行",
        "script": "devflow.py",
        "example": "devflow full --dir ."
    },
    "selftest": {
        "desc": "自测",
        "script": "selftest.py",
        "example": "devflow selftest"
    },
    "setup": {
        "desc": "一键接入 AI 平台 (claude/codex/opencode/cursor/windsurf/trae/copilot)",
        "script": "setup.py",
        "example": "devflow setup install --target <项目目录>"
    },
    "todo": {
        "desc": "TODO/FIXME 标记扫描",
        "script": "todo-scan.py",
        "example": "devflow todo --dir ."
    },
    "complexity": {
        "desc": "代码复杂度分析",
        "script": "complexity.py",
        "example": "devflow complexity --dir src/ --threshold 10"
    },
    "gitstats": {
        "desc": "Git 提交统计分析",
        "script": "git-stats.py",
        "example": "devflow gitstats --dir ."
    },
    "workflow": {
        "desc": "阶段化工作流引擎 (init/plan/code/verify/review)",
        "script": "workflow.py",
        "example": "devflow workflow init --dir ."
    },
    "agents": {
        "desc": "多 Agent 协作 (pm/architect/developer/qa/reviewer)",
        "script": "agents.py",
        "example": "devflow agents --team qa,reviewer --dir ."
    },
    "doctor": {
        "desc": "项目健康诊断",
        "script": "doctor.py",
        "example": "devflow doctor --dir ."
    },
    "audit": {
        "desc": "深度安全审计",
        "script": "security-audit.py",
        "example": "devflow audit --dir ."
    },
    "pr": {
        "desc": "PR 合并检查",
        "script": "pr-tool.py",
        "example": "devflow pr --diff pr.diff"
    },
    "tdd": {
        "desc": "TDD 实践检查",
        "script": "tdd-check.py",
        "example": "devflow tdd --dir ."
    },
    "map": {
        "desc": "代码地图",
        "script": "code-map.py",
        "example": "devflow map --dir ."
    },
    "memory": {
        "desc": "项目记忆管理",
        "script": "memory.py",
        "example": "devflow memory add '决策内容'"
    },
    "refactor": {
        "desc": "重构建议",
        "script": "refactor.py",
        "example": "devflow refactor --dir ."
    },
    "release": {
        "desc": "发布说明生成",
        "script": "release-notes.py",
        "example": "devflow release --dir ."
    },
    "onboarding": {
        "desc": "新成员项目导览",
        "script": "onboarding.py",
        "example": "devflow onboarding --dir ."
    },
    "coverage": {
        "desc": "测试覆盖率估算",
        "script": "coverage-scan.py",
        "example": "devflow coverage --dir ."
    }
}


def show_help():
    """显示帮助信息"""
    print("DevFlow CLI - 一站式全链路开发辅助工具\n")
    print("用法: devflow <command> [options]\n")
    print("可用命令:")
    for cmd, info in COMMANDS.items():
        print(f"  {cmd:<12} {info['desc']}")
    print("\n示例:")
    for cmd, info in list(COMMANDS.items())[:5]:
        print(f"  {info['example']}")
    print("\n更多帮助: devflow <command> --help")


def main(argv=None):
    argv = list(sys.argv[1:] if argv is None else argv)
    if not argv or argv[0] in ("-h", "--help", "help"):
        show_help()
        return 0

    command = argv[0]

    if command not in COMMANDS:
        print(f"错误: 未知命令 '{command}'")
        print(f"运行 'devflow help' 查看可用命令")
        return 2

    # setup 命令特殊处理：setup.py 位于 share/devflow/（scripts 的上一级）
    if command == "setup":
        setup_script = SCRIPTS_DIR.parent / "setup.py"
        if not setup_script.exists():
            setup_script = _REPO_SCRIPTS.parent / "setup.py"
        if not setup_script.exists():
            print(f"错误: 找不到 setup.py，请在 DevFlow 仓库目录下运行，或重新 pip install .")
            return 2
        cmd = [sys.executable, str(setup_script)] + argv[1:]
        result = subprocess.run(cmd)
        return result.returncode

    script = SCRIPTS_DIR / COMMANDS[command]["script"]
    args = argv[1:]

    if not script.exists():
        print(f"错误: 脚本不存在 {script}")
        print("若已通过 pip 安装，请确认 scripts/ 已随包安装；"
              "或在仓库目录下运行。")
        return 2

    cmd = [sys.executable, str(script)] + args
    result = subprocess.run(cmd)
    return result.returncode


if __name__ == "__main__":
    sys.exit(main())
