#!/usr/bin/env python3
"""
DevFlow CLI - 统一命令行入口
用法: python devflow-cli.py <command> [options]
"""

import sys
import subprocess
from pathlib import Path

SCRIPTS_DIR = Path(__file__).parent / "scripts"

COMMANDS = {
    "review": {
        "desc": "代码审查 (安全/逻辑/性能)",
        "script": "review.py",
        "example": "devflow review --mode security --dir ."
    },
    "explain": {
        "desc": "代码解释 (代码→人话)",
        "script": "explain.py",
        "example": "devflow explain --file main.py"
    },
    "testgen": {
        "desc": "测试用例生成",
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
        "desc": "语法/语言转换",
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
        "example": "devflow config --mode docker"
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
    print("用法: python devflow-cli.py <command> [options]\n")
    print("可用命令:")
    for cmd, info in COMMANDS.items():
        print(f"  {cmd:<12} {info['desc']}")
    print("\n示例:")
    for cmd, info in list(COMMANDS.items())[:5]:
        print(f"  {info['example']}")
    print("\n更多帮助: python devflow-cli.py <command> --help")


def main():
    if len(sys.argv) < 2 or sys.argv[1] in ("-h", "--help", "help"):
        show_help()
        return

    command = sys.argv[1]

    if command not in COMMANDS:
        print(f"错误: 未知命令 '{command}'")
        print(f"运行 'python devflow-cli.py help' 查看可用命令")
        return

    script = SCRIPTS_DIR / COMMANDS[command]["script"]
    args = sys.argv[2:]

    if not script.exists():
        print(f"错误: 脚本不存在 {script}")
        return

    cmd = [sys.executable, str(script)] + args
    result = subprocess.run(cmd, cwd=Path(__file__).parent)
    sys.exit(result.returncode)


if __name__ == "__main__":
    main()
